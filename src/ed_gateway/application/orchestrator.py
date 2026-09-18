from __future__ import annotations

from uuid import UUID

from ed_gateway.application.drafts import DraftGenerator
from ed_gateway.application.extractor import ResponseExtractor, SafetyScanDegraded
from ed_gateway.application.planner import QuestionPlanner
from ed_gateway.application.repository import InterviewRepository
from ed_gateway.application.safety import SafetyGate
from ed_gateway.application.session_manager import InterviewSessionManager
from ed_gateway.domain.models import (
    CreateSessionRequest,
    DraftPayload,
    FieldStatus,
    InformationSource,
    InterviewPhase,
    InterviewState,
    SafetyStatus,
    TurnResponse,
)

INTRODUCTION = (
    "**研究展示用途｜僅使用合成資料**\n\n"
    "ED Gateway 會協助蒐集並整理資料，交由檢傷護理師確認；本系統不會診斷、"
    "不決定治療或看診順序。填答期間若病人變得更不舒服，請立刻舉手或通知現場人員。\n\n"
    "現在操作的是病人本人，還是家屬或陪同者？"
)

URGENT_MESSAGE = (
    "# 請立即呼叫檢傷護理師\n\n"
    "請按現場求助按鈕、舉手，或直接大聲呼叫護理師。一般提問已停止，"
    "已取得的資料會整理為警訊摘要供護理師確認。"
)


class InterviewOrchestrator:
    def __init__(
        self,
        *,
        repository: InterviewRepository,
        session_manager: InterviewSessionManager,
        extractor: ResponseExtractor,
        safety_gate: SafetyGate,
        planner: QuestionPlanner,
        draft_generator: DraftGenerator,
    ) -> None:
        self._repository = repository
        self._session_manager = session_manager
        self._extractor = extractor
        self._safety_gate = safety_gate
        self._planner = planner
        self._draft_generator = draft_generator

    async def create_session(self, request: CreateSessionRequest) -> TurnResponse:
        state = await self._session_manager.create(
            interaction_mode=request.interaction_mode,
            answer_language=request.answer_language,
        )
        state.asked_question_ids.append("respondent_type")
        await self._repository.create_session(state, INTRODUCTION)
        return self._response(state, INTRODUCTION, "respondent_type")

    async def handle_message(self, session_id: UUID, content: str) -> TurnResponse:
        state = await self._require_state(session_id)
        if state.phase in {InterviewPhase.ESCALATED, InterviewPhase.DRAFT_READY, InterviewPhase.STOPPED}:
            draft = await self._repository.get_draft(session_id)
            message = (
                "此訪談已停止，請由檢傷護理師接手。"
                if state.phase == InterviewPhase.ESCALATED
                else "此訪談已完成；可檢視護理紀錄草稿。"
            )
            return self._response(state, message, draft=draft, completed=True)

        question_id = state.asked_question_ids[-1]
        question = self._planner.question_by_id(question_id)
        source = self._message_source(state, content)
        await self._repository.record_user_message(session_id, content, source)
        prior = state.observations.get(question.target_field)
        try:
            observations = await self._extractor.extract(
                text=content, expected_field=question.target_field, state=state
            )
        except SafetyScanDegraded as degraded:
            observations = degraded.partial_observations
            state.safety_scan_degraded.append(content)
        for observation in observations:
            ambiguous_statuses = {FieldStatus.NEEDS_CLARIFICATION}
            if observation.field_key.startswith("safety."):
                ambiguous_statuses.add(FieldStatus.UNKNOWN)
            if observation.status in ambiguous_statuses and prior is not None and prior.status in ambiguous_statuses:
                state.clarification_counts[observation.field_key] = (
                    state.clarification_counts.get(observation.field_key, 0) + 1
                )
            self._session_manager.update(state, observation)

        decision = self._safety_gate.evaluate(state)
        state.safety_status = decision.status
        if decision.status == SafetyStatus.TRIGGERED:
            self._session_manager.escalate(state, decision.triggered_rule_ids)
            draft = self._draft_generator.generate(state)
            await self._repository.save_turn(
                state=state,
                patient_message=URGENT_MESSAGE,
                event_type="SAFETY_ESCALATED",
                event_payload={"triggered_rule_ids": decision.triggered_rule_ids},
                draft=draft,
            )
            return self._response(state, URGENT_MESSAGE, draft=draft, completed=True)

        if decision.requires_clarification and decision.clarification_field:
            next_question = self._planner.question_for_field(decision.clarification_field)
            if next_question is None:
                raise RuntimeError("no clarification question configured")
            state.phase = InterviewPhase.SAFETY_SCREEN
            state.asked_question_ids.append(next_question.id)
            message = next_question.clarification_wording or next_question.wording
            await self._repository.save_turn(
                state=state,
                patient_message=message,
                event_type="CLARIFICATION_REQUESTED",
                event_payload={"field": decision.clarification_field},
            )
            return self._response(state, message, next_question.id)

        next_question = self._planner.next_question(state)
        if next_question is None:
            return await self._complete(
                state=state,
                event_type="INTERVIEW_COMPLETED",
            )

        state.phase = self._planner.phase_for(next_question)
        state.asked_question_ids.append(next_question.id)
        await self._repository.save_turn(
            state=state,
            patient_message=next_question.wording,
            event_type="ANSWER_RECORDED",
            event_payload={
                "question_id": question_id,
                "observation_fields": [item.field_key for item in observations],
            },
        )
        return self._response(state, next_question.wording, next_question.id)

    async def finish(self, session_id: UUID) -> TurnResponse:
        state = await self._require_state(session_id)
        existing = await self._repository.get_draft(session_id)
        if existing:
            return self._response(
                state,
                "已產生護理紀錄草稿，請交由檢傷護理師確認。",
                draft=existing,
                completed=True,
            )
        return await self._complete(
            state=state,
            event_type="EARLY_COMPLETION_REQUESTED",
        )

    async def get_state(self, session_id: UUID) -> InterviewState:
        return await self._require_state(session_id)

    async def get_draft(self, session_id: UUID) -> DraftPayload | None:
        await self._require_state(session_id)
        return await self._repository.get_draft(session_id)

    async def _complete(
        self,
        *,
        state: InterviewState,
        event_type: str,
    ) -> TurnResponse:
        self._session_manager.finish(state)
        draft = self._draft_generator.generate(state)
        message = "已產生護理紀錄草稿，請交由檢傷護理師確認。"
        await self._repository.save_turn(
            state=state,
            patient_message=message,
            event_type=event_type,
            event_payload={"missing_fields": draft.structured["missing_fields"]},
            draft=draft,
        )
        return self._response(state, message, draft=draft, completed=True)

    async def _require_state(self, session_id: UUID) -> InterviewState:
        state = await self._session_manager.retrieve(session_id)
        if state is None:
            raise KeyError(str(session_id))
        return state

    @staticmethod
    def _message_source(state: InterviewState, content: str) -> InformationSource:
        if state.respondent_type.value == "CAREGIVER":
            return InformationSource.CAREGIVER_STATEMENT
        if state.respondent_type.value == "UNKNOWN" and any(marker in content for marker in ("家屬", "陪同", "照顧者")):
            return InformationSource.CAREGIVER_STATEMENT
        return InformationSource.PATIENT_STATEMENT

    @staticmethod
    def _response(
        state: InterviewState,
        message: str,
        next_question_id: str | None = None,
        *,
        draft: DraftPayload | None = None,
        completed: bool = False,
    ) -> TurnResponse:
        return TurnResponse(
            session_id=state.session_id,
            phase=state.phase,
            patient_message=message,
            next_question_id=next_question_id,
            safety_status=state.safety_status,
            triggered_rule_ids=state.triggered_rule_ids,
            completed=completed,
            draft=draft,
        )
