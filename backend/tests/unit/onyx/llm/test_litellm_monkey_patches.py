from typing import Any
from types import SimpleNamespace

from litellm.llms.ollama.chat.transformation import OllamaChatCompletionResponseIterator
from litellm.llms.openai.responses.transformation import OpenAIResponsesAPIConfig
from litellm.litellm_core_utils.litellm_logging import Logging
from litellm.types.llms.openai import ResponseAPIUsage
from litellm.types.llms.openai import ResponseCompletedEvent
from litellm.types.llms.openai import ResponsesAPIStreamEvents
from litellm.types.llms.openai import ResponsesAPIResponse
from litellm.types.responses.main import GenericResponseOutputItem

from onyx.llm.litellm_singleton.monkey_patches import apply_monkey_patches

_UNSET = object()


def _create_iterator() -> OllamaChatCompletionResponseIterator:
    apply_monkey_patches()
    return OllamaChatCompletionResponseIterator(
        streaming_response=iter(()),
        sync_stream=True,
    )


def _build_chunk(
    *,
    thinking: object = _UNSET,
    content: object = _UNSET,
) -> dict[str, Any]:
    message: dict[str, Any] = {"role": "assistant"}
    if thinking is not _UNSET:
        message["thinking"] = thinking
    if content is not _UNSET:
        message["content"] = content

    return {
        "model": "llama3.1",
        "message": message,
        "done": False,
        "prompt_eval_count": 0,
        "eval_count": 0,
    }


def test_ollama_chunk_parser_transitions_from_native_thinking_to_content() -> None:
    iterator = _create_iterator()

    thinking_chunk = _build_chunk(thinking="Let me think")
    content_chunk = _build_chunk(thinking="", content="Final answer")

    thinking_response = iterator.chunk_parser(thinking_chunk)
    content_response = iterator.chunk_parser(content_chunk)

    assert thinking_response.choices[0].delta.reasoning_content == "Let me think"
    assert thinking_response.choices[0].delta.content is None

    assert getattr(content_response.choices[0].delta, "reasoning_content", None) is None
    assert content_response.choices[0].delta.content == "Final answer"
    assert iterator.finished_reasoning_content is True


def test_ollama_chunk_parser_keeps_tagged_thinking_until_close_tag() -> None:
    iterator = _create_iterator()

    start_chunk = _build_chunk(content="<think>step 1")
    middle_chunk = _build_chunk(content="step 2")
    close_chunk = _build_chunk(content="final</think>")

    start_response = iterator.chunk_parser(start_chunk)
    middle_response = iterator.chunk_parser(middle_chunk)
    close_response = iterator.chunk_parser(close_chunk)

    assert start_response.choices[0].delta.reasoning_content == "step 1"
    assert start_response.choices[0].delta.content is None

    assert middle_response.choices[0].delta.reasoning_content == "step 2"
    assert middle_response.choices[0].delta.content is None

    assert getattr(close_response.choices[0].delta, "reasoning_content", None) is None
    assert close_response.choices[0].delta.content == "final"
    assert iterator.finished_reasoning_content is True


def test_ollama_chunk_parser_handles_think_tag_after_native_thinking() -> None:
    iterator = _create_iterator()

    native_thinking_chunk = _build_chunk(thinking="native reasoning")
    tagged_thinking_chunk = _build_chunk(content="<think>tagged reasoning")

    iterator.chunk_parser(native_thinking_chunk)
    tagged_response = iterator.chunk_parser(tagged_thinking_chunk)

    assert tagged_response.choices[0].delta.reasoning_content == "tagged reasoning"
    assert tagged_response.choices[0].delta.content is None


def test_ollama_chunk_parser_preserves_content_when_thinking_and_content_coexist() -> (
    None
):
    iterator = _create_iterator()

    combined_chunk = _build_chunk(
        thinking="Need one thought",
        content="Visible answer token",
    )

    response = iterator.chunk_parser(combined_chunk)

    assert response.choices[0].delta.reasoning_content == "Need one thought"
    assert response.choices[0].delta.content == "Visible answer token"


def _build_responses_api_response() -> ResponsesAPIResponse:
    output_item = GenericResponseOutputItem(
        type="message",
        id="msg_1",
        status="completed",
        role="assistant",
        content=[],
    )
    return ResponsesAPIResponse(
        id="resp_1",
        created_at=1,
        model="gpt-5.5",
        object="response",
        output=[output_item],
        usage=ResponseAPIUsage(
            input_tokens=1,
            output_tokens=2,
            total_tokens=3,
        ),
    )


def _assemble_streaming_response(result: ResponseCompletedEvent) -> Any:
    apply_monkey_patches()
    return Logging._get_assembled_streaming_response(
        SimpleNamespace(stream=True),
        result,
        start_time=None,
        end_time=None,
        is_async=False,
        streaming_chunks=[],
    )


def test_responses_streaming_logging_patch_preserves_output_item_types() -> None:
    assembled = _assemble_streaming_response(
        ResponseCompletedEvent(
            type="response.completed",
            response=_build_responses_api_response(),
        )
    )

    assert isinstance(assembled, ResponsesAPIResponse)
    assert isinstance(assembled.usage, ResponseAPIUsage)
    assert isinstance(assembled.output[0], GenericResponseOutputItem)
    assert hasattr(assembled.output[0], "model_dump")


def test_responses_streaming_logging_patch_handles_dict_response() -> None:
    event = ResponseCompletedEvent.model_construct(
        type="response.completed",
        response=_build_responses_api_response().model_dump(),
    )

    assembled = _assemble_streaming_response(event)

    assert isinstance(assembled, ResponsesAPIResponse)
    assert isinstance(assembled.usage, ResponseAPIUsage)
    assert not isinstance(assembled.output[0], dict)
    assert hasattr(assembled.output[0], "model_dump")


def test_responses_streaming_logging_patch_handles_dict_output() -> None:
    response_data = _build_responses_api_response().model_dump()
    response_data["output"] = response_data["output"][0]
    event = ResponseCompletedEvent.model_construct(
        type="response.completed",
        response=response_data,
    )

    assembled = _assemble_streaming_response(event)

    assert isinstance(assembled, ResponsesAPIResponse)
    assert isinstance(assembled.usage, ResponseAPIUsage)
    assert isinstance(assembled.output, list)
    assert len(assembled.output) == 1
    assert not isinstance(assembled.output[0], dict)
    assert hasattr(assembled.output[0], "model_dump")


def _transform_response_completed_chunk(response_data: dict[str, Any]) -> Any:
    apply_monkey_patches()
    return OpenAIResponsesAPIConfig().transform_streaming_response(
        model="gpt-5.5",
        parsed_chunk={
            "type": ResponsesAPIStreamEvents.RESPONSE_COMPLETED.value,
            "response": response_data,
        },
        logging_obj=SimpleNamespace(),
    )


def test_openai_responses_streaming_transform_normalizes_dict_output() -> None:
    response_data = _build_responses_api_response().model_dump()
    response_data["output"] = response_data["output"][0]

    event = _transform_response_completed_chunk(response_data)

    assert isinstance(event, ResponseCompletedEvent)
    assert isinstance(event.response, ResponsesAPIResponse)
    assert isinstance(event.response.output, list)
    assert len(event.response.output) == 1


def test_openai_responses_streaming_transform_handles_unusable_output_shapes() -> None:
    for output in (None, "hello", ["hello"]):
        response_data = _build_responses_api_response().model_dump()
        response_data["output"] = output

        event = _transform_response_completed_chunk(response_data)

        assert isinstance(event, ResponseCompletedEvent)
        assert isinstance(event.response, ResponsesAPIResponse)
        assert event.response.output == []
