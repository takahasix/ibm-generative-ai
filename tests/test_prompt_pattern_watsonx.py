from unittest.mock import MagicMock, patch

import pytest
from pytest_httpx import HTTPXMock

from genai.credentials import Credentials
from genai.prompt_pattern import PromptPattern
from genai.routers import PromptTemplateRouter
from genai.schemas.responses import WatsonxTemplate
from tests.assets.response_helper import SimpleResponse
from tests.utils import match_endpoint


@pytest.mark.unit
class TestPromptPattern:
    def setup_method(self):
        self.credentials = Credentials("KEY")
        self.string_template = "{{input}}:{{ouptu}}"
        self.name = "io"

        self.expected_resp = SimpleResponse.prompt_template(template=self.string_template, name=self.name)
        self.template = WatsonxTemplate.model_validate(self.expected_resp["results"])

    def test_from_watsonx(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url=match_endpoint(PromptTemplateRouter.PROMPT_TEMPLATES), method="POST", json=self.expected_resp
        )

        pt = PromptPattern.from_watsonx(credentials=self.credentials, template=self.string_template, name=self.name)
        assert isinstance(pt, PromptPattern)
        assert str(pt) == self.string_template
        assert pt.watsonx == self.template

    @patch("genai.services.PromptTemplateManager.load_template")
    @patch("genai.services.PromptTemplateManager.update_template")
    @patch("genai.services.PromptTemplateManager.save_template")
    def test_from_watsonx_logic(self, save, update, load):
        # Cases :
        # fetching an existing template : name OR id
        # updating an existing template : template + (name OR id)
        # creating a new template       : template + name

        # Case 1 : fetching an existing template
        PromptPattern.from_watsonx(credentials=self.credentials, name=self.name)
        load.assert_called_with(credentials=self.credentials, name=self.name, id=None)

        PromptPattern.from_watsonx(credentials=self.credentials, id="_id")
        load.assert_called_with(credentials=self.credentials, id="_id", name=None)

        # Case 2 : updating an existing template
        load.return_value = self.template
        _id = self.template.id
        _name = self.template.name

        PromptPattern.from_watsonx(credentials=self.credentials, id=_id, template="Instruction: {{instruction}}")
        update.assert_called_with(
            credentials=self.credentials, id=_id, template="Instruction: {{instruction}}", name=_name
        )

        PromptPattern.from_watsonx(credentials=self.credentials, name=_name, template="Instruction: {{instruction}}")
        update.assert_called_with(
            credentials=self.credentials, id=_id, template="Instruction: {{instruction}}", name=_name
        )

        # Case 3 : saving a new template
        load.side_effect = Exception(MagicMock(status=404), "not found")
        _name = self.template.name

        PromptPattern.from_watsonx(credentials=self.credentials, template="Instruction: {{instruction}}", name=_name)
        save.assert_called_with(credentials=self.credentials, template="Instruction: {{instruction}}", name=_name)

    def test_pp_watsonx_delete(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url=match_endpoint(PromptTemplateRouter.PROMPT_TEMPLATES), method="POST", json=self.expected_resp
        )
        httpx_mock.add_response(
            url=match_endpoint(PromptTemplateRouter.PROMPT_TEMPLATES, self.template.id),
            method="DELETE",
            json=self.expected_resp,
        )

        pt = PromptPattern.from_watsonx(credentials=self.credentials, template=self.string_template, name=self.name)

        id = pt.delete()
        assert id == self.template.id
