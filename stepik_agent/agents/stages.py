from models.schemas import AgentStage


STAGE_LABELS_RU = {
    AgentStage.WELCOME: "Приветствие",
    AgentStage.COLLECT_GOAL: "Сбор цели обучения",
    AgentStage.COLLECT_DETERMINISTIC: "Сбор параметров поиска",
    AgentStage.GENERATE_QUERIES: "Генерация поисковых запросов",
    AgentStage.SEARCH_INITIAL: "Первичный поиск на Stepik",
    AgentStage.REVIEW_RESULTS: "Анализ первичной выдачи",
    AgentStage.REFINE_QUERIES: "Уточнение запросов",
    AgentStage.SEARCH_REFINED: "Повторный поиск",
    AgentStage.FRESHNESS_CHECK: "Проверка актуальности 2026",
    AgentStage.RANK: "Ранжирование курсов",
    AgentStage.PRESENT: "Формирование ответа",
    AgentStage.FOLLOW_UP: "Уточнения пользователя",
    AgentStage.ENROLL_CONFIRM: "Подтверждение записи на курс",
}


def stage_banner(stage: AgentStage) -> str:
    label = STAGE_LABELS_RU.get(stage, stage.value)
    return f"### Этап: {label}"
