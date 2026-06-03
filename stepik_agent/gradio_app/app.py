import gradio as gr
from gradio.components.chatbot import ChatMessage

from stepik_agent.agents.orchestrator import AgentOrchestrator, WELCOME_TEXT
from stepik_agent.agents.stages import stage_banner
from stepik_agent.config import load_settings
from stepik_agent.logging_setup import setup_logging
from models.schemas import AgentStage


def _as_messages(history) -> list[ChatMessage]:
    if history is None:
        return []
    out: list[ChatMessage] = []
    for item in history:
        if isinstance(item, ChatMessage):
            out.append(item)
            continue
        if isinstance(item, dict):
            out.append(
                ChatMessage(
                    role=item.get("role", "assistant"),
                    content=str(item.get("content", "")),
                )
            )
    return out


def build_app() -> gr.Blocks:
    settings = load_settings()
    setup_logging(settings.log_dir)
    orchestrator = AgentOrchestrator(settings)
    orchestrator.bootstrap_preferences()

    welcome = [ChatMessage(role="assistant", content=WELCOME_TEXT)]

    def on_send(message: str, history) -> tuple:
        messages = _as_messages(history)
        if not message.strip():
            stage = stage_banner(orchestrator.stage)
            return messages, messages, stage, ""

        reply = orchestrator.handle_message(message)
        messages.append(ChatMessage(role="user", content=message))
        messages.append(ChatMessage(role="assistant", content=reply))
        stage = stage_banner(orchestrator.stage)
        return messages, messages, stage, ""

    with gr.Blocks(title="Stepik Agent") as demo:
        gr.Markdown("# Stepik course agent")
        stage_box = gr.Textbox(
            label="Текущий этап",
            value=stage_banner(AgentStage.COLLECT_GOAL),
            interactive=False,
        )
        chat = gr.Chatbot(label="Диалог", value=welcome)
        state = gr.State(welcome)
        msg = gr.Textbox(label="Сообщение", placeholder="Опишите цель обучения…")
        send = gr.Button("Отправить")

        send.click(on_send, [msg, state], [state, chat, stage_box, msg])
        msg.submit(on_send, [msg, state], [state, chat, stage_box, msg])

    return demo


def launch() -> None:
    build_app().launch()
