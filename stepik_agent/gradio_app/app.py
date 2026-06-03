import gradio as gr

from stepik_agent.agents.orchestrator import AgentOrchestrator, WELCOME_TEXT
from stepik_agent.agents.stages import stage_banner
from stepik_agent.config import load_settings
from stepik_agent.logging_setup import setup_logging
from models.schemas import AgentStage


def build_app() -> gr.Blocks:
    settings = load_settings()
    setup_logging(settings.log_dir)
    orchestrator = AgentOrchestrator(settings)
    orchestrator.bootstrap_preferences()

    def respond(message: str, history: list) -> tuple:
        if not message.strip():
            return history, history
        reply = orchestrator.handle_message(message)
        history = history + [
            {"role": "user", "content": message},
            {"role": "assistant", "content": reply},
        ]
        return history, history

    with gr.Blocks(title="Stepik Agent") as demo:
        gr.Markdown("# Stepik course agent")
        stage_box = gr.Textbox(
            label="Текущий этап",
            value=stage_banner(AgentStage.WELCOME),
            interactive=False,
        )
        chat = gr.Chatbot(label="Диалог", type="messages", value=[])
        state = gr.State([])
        msg = gr.Textbox(label="Сообщение", placeholder="Опишите цель обучения…")
        send = gr.Button("Отправить")

        def on_send(message, history, st):
            new_hist, new_st = respond(message, st or history)
            stage = stage_banner(orchestrator.stage)
            return new_hist, new_hist, stage

        send.click(on_send, [msg, chat, state], [chat, state, stage_box])
        msg.submit(on_send, [msg, chat, state], [chat, state, stage_box])
        demo.load(
            lambda: ([{"role": "assistant", "content": WELCOME_TEXT}], WELCOME_TEXT),
            outputs=[chat, stage_box],
        )

    return demo


def launch() -> None:
    build_app().launch()
