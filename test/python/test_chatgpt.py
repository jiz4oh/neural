import json
import sys
import urllib.error
import urllib.request
from io import BytesIO
from typing import Any, Dict, Optional, cast
from unittest import mock

import pytest

from neural_providers import chatgpt


def get_valid_config() -> Dict[str, Any]:
    return {
        "api_key": ".",
        "model": "foo",
        "prompt": "say hello",
        "temperature": 1,
        "top_p": 1,
        "max_tokens": 1,
        "presence_penalty": 1,
        "frequency_penalty": 1,
    }


def test_load_config_errors():
    with pytest.raises(ValueError) as exc:
        chatgpt.load_config(cast(Any, 0))

    assert str(exc.value) == "chatgpt config is not a dictionary"

    config: Dict[str, Any] = {}

    for modification, expected_error in [
        ({}, "chatgpt.api_key is not defined"),
        ({"api_key": ""}, "chatgpt.api_key is not defined"),
        ({"api_key": "."}, "chatgpt.model is not defined"),
        ({"model": ""}, "chatgpt.model is not defined"),
        (
            {"model": "x", "temperature": "x"},
            "chatgpt.temperature is invalid"
        ),
        (
            {"temperature": 1, "top_p": "x"},
            "chatgpt.top_p is invalid"
        ),
        (
            {"top_p": 1, "max_tokens": "x"},
            "chatgpt.max_tokens is invalid"
        ),
        (
            {"max_tokens": 1, "presence_penalty": "x"},
            "chatgpt.presence_penalty is invalid"
        ),
        (
            {"presence_penalty": 1, "frequency_penalty": "x"},
            "chatgpt.frequency_penalty is invalid"
        ),
    ]:
        config.update(modification)

        with pytest.raises(ValueError) as exc:
            chatgpt.load_config(config)

        assert str(exc.value) == expected_error, config


def test_main_function_rate_other_error():
    with mock.patch.object(sys.stdin, 'readline') as readline_mock, \
        mock.patch.object(chatgpt, 'get_chatgpt_completion') as compl_mock:

        compl_mock.side_effect = urllib.error.HTTPError(
            url='',
            msg='',
            hdrs=mock.Mock(),
            fp=None,
            code=500,
        )
        readline_mock.return_value = json.dumps({
            "config": get_valid_config(),
            "prompt": "hello there",
        })

        with pytest.raises(urllib.error.HTTPError):
            chatgpt.main()


def test_print_chatgpt_results():
    result_data = (
        b'data: {"id":"chatcmpl-6tMwjovREOTA84MkGBOS5rWyj1izv","object":"chat.completion.chunk","created":1678654265,"model":"gpt-3.5-turbo-0301","choices":[{"delta":{"role":"assistant"},"index":0,"finish_reason":null}]}\n'  # noqa
        b'\n'
        b'data: {"id":"chatcmpl-6tMwjovREOTA84MkGBOS5rWyj1izv","object":"chat.completion.chunk","created":1678654265,"model":"gpt-3.5-turbo-0301","choices":[{"delta":{"content":"\\n\\n"},"index":0,"finish_reason":null}]}\n'  # noqa
        b'\n'
        b'data: {"id":"chatcmpl-6tMwjovREOTA84MkGBOS5rWyj1izv","object":"chat.completion.chunk","created":1678654265,"model":"gpt-3.5-turbo-0301","choices":[{"delta":{"content":"This"},"index":0,"finish_reason":null}]}\n'  # noqa
        b'\n'
        b'data: {"id":"chatcmpl-6tMwjovREOTA84MkGBOS5rWyj1izv","object":"chat.completion.chunk","created":1678654265,"model":"gpt-3.5-turbo-0301","choices":[{"delta":{"content":" is"},"index":0,"finish_reason":null}]}\n'  # noqa
        b'\n'
        b'data: {"id":"chatcmpl-6tMwjovREOTA84MkGBOS5rWyj1izv","object":"chat.completion.chunk","created":1678654265,"model":"gpt-3.5-turbo-0301","choices":[{"delta":{"content":" a"},"index":0,"finish_reason":null}]}\n'  # noqa
        b'\n'
        b'data: {"id":"chatcmpl-6tMwjovREOTA84MkGBOS5rWyj1izv","object":"chat.completion.chunk","created":1678654265,"model":"gpt-3.5-turbo-0301","choices":[{"delta":{"content":" test"},"index":0,"finish_reason":null}]}\n'  # noqa
        b'\n'
        b'data: {"id":"chatcmpl-6tMwjovREOTA84MkGBOS5rWyj1izv","object":"chat.completion.chunk","created":1678654265,"model":"gpt-3.5-turbo-0301","choices":[{"delta":{"content":"."},"index":0,"finish_reason":null}]}\n'  # noqa
        b'\n'
        b'data: {"id":"chatcmpl-6tMwjovREOTA84MkGBOS5rWyj1izv","object":"chat.completion.chunk","created":1678654265,"model":"gpt-3.5-turbo-0301","choices":[{"delta":{},"index":0,"finish_reason":"length"}]}\n'  # noqa
        b'\n'
        b'data: [DONE]\n'
        b'\n'
    )

    with mock.patch.object(sys.stdin, 'readline') as readline_mock, \
        mock.patch.object(urllib.request, 'urlopen') as urlopen_mock, \
        mock.patch('builtins.print') as print_mock:

        urlopen_mock.return_value.__enter__.return_value = BytesIO(result_data)

        readline_mock.return_value = json.dumps({
            "config": get_valid_config(),
            "prompt": "Say this is a test",
        })
        chatgpt.main()

    assert print_mock.call_args_list == [
        mock.call('\n\n', end='', flush=True),
        mock.call('This', end='', flush=True),
        mock.call(' is', end='', flush=True),
        mock.call(' a', end='', flush=True),
        mock.call(' test', end='', flush=True),
        mock.call('.', end='', flush=True),
        mock.call(),
    ]


def test_main_function_bad_config():
    with mock.patch.object(sys.stdin, 'readline') as readline_mock, \
        mock.patch.object(chatgpt, 'load_config') as load_config_mock:

        load_config_mock.side_effect = ValueError("expect this")
        readline_mock.return_value = json.dumps({"config": {}})

        with pytest.raises(SystemExit) as exc:
            chatgpt.main()

    assert str(exc.value) == 'expect this'


@pytest.mark.parametrize(
    'code, error_text, expected_message',
    (
        pytest.param(
            429,
            None,
            'OpenAI request limit reached!',
            id="request_limit",
        ),
        pytest.param(
            400,
            '{]',
            'OpenAI request failure: {]',
            id="error_with_mangled_json",
        ),
        pytest.param(
            400,
            json.dumps({'error': {}}),
            'OpenAI request failure: {"error": {}}',
            id="error_with_missing_message_key",
        ),
        pytest.param(
            400,
            json.dumps({
                'error': {
                    'message': "This model's maximum context length is 123",
                },
            }),
            'OpenAI request failure: Too much text for a request!',
            id="too_much_text",
        ),
        pytest.param(
            401,
            json.dumps({
                'error': {
                    'message': "Bad authentication error",
                },
            }),
            'OpenAI request failure: Bad authentication error',
            id="unauthorised_failure",
        ),
    )
)
def test_api_error(
    code: int,
    error_text: Optional[str],
    expected_message: str,
):
    with mock.patch.object(sys.stdin, 'readline') as readline_mock, \
        mock.patch.object(chatgpt, 'get_chatgpt_completion') as compl_mock:

        compl_mock.side_effect = urllib.error.HTTPError(
            url='',
            msg='',
            hdrs=mock.Mock(),
            fp=BytesIO(error_text.encode('utf-8')) if error_text else None,
            code=code,
        )

        readline_mock.return_value = json.dumps({
            "config": get_valid_config(),
            "prompt": "hello there",
        })

        with pytest.raises(SystemExit) as exc:
            chatgpt.main()

    assert str(exc.value) == f'Neural error: {expected_message}'
