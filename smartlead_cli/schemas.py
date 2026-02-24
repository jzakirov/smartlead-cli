"""Pydantic schemas for curated Smartlead CLI JSON bodies.

Strict by default (`extra="forbid"`), but intentionally scoped to curated commands.
`raw` remains the escape hatch and is not validated here.
"""

from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, StrictStr, ValidationError
from pydantic import field_validator, model_validator


class CliSchemaModel(BaseModel):
    """Pydantic base model with compact CLI-friendly error formatting."""

    model_config = ConfigDict(extra="forbid")
    cli_label: ClassVar[str] = "payload"

    @classmethod
    def model_validate(  # type: ignore[override]
        cls,
        obj: Any,
        *,
        strict: bool | None = None,
        extra: str | None = None,
        from_attributes: bool | None = None,
        context: Any | None = None,
        by_alias: bool | None = None,
        by_name: bool | None = None,
    ):
        try:
            return super().model_validate(
                obj,
                strict=strict,
                extra=extra,
                from_attributes=from_attributes,
                context=context,
                by_alias=by_alias,
                by_name=by_name,
            )
        except ValidationError as exc:
            messages: list[str] = []
            for err in exc.errors():
                loc = ".".join(str(part) for part in err.get("loc", []))
                msg = err.get("msg", "invalid value")
                messages.append(f"{loc}: {msg}" if loc else msg)
            raise ValueError(f"{cls.cli_label} failed validation ({'; '.join(messages)})") from exc


class OooSettingsModel(CliSchemaModel):
    model_config = ConfigDict(extra="forbid")
    cli_label = "campaign update body.out_of_office_detection_settings"

    ignoreOOOasReply: StrictBool | None = None
    autoReactivateOOO: StrictBool | None = None
    reactivateOOOwithDelay: StrictStr | None = None
    autoCategorizeOOO: StrictBool | None = None


class CampaignCreateBodyModel(CliSchemaModel):
    cli_label = "campaign create body"

    name: StrictStr
    client_id: StrictInt | None = None


class CampaignUpdateBodyModel(CliSchemaModel):
    cli_label = "campaign update body"

    track_settings: list[StrictStr] | None = None
    stop_lead_settings: StrictStr | None = None
    unsubscribe_text: StrictStr | None = None
    send_as_plain_text: StrictBool | None = None
    follow_up_percentage: StrictInt | None = Field(default=None, ge=0, le=100)
    client_id: StrictInt | None = None
    enable_ai_esp_matching: StrictBool | None = None
    name: StrictStr | None = None
    force_plain_text: StrictBool | None = None
    auto_pause_domain_leads_on_reply: StrictBool | None = None
    ignore_ss_mailbox_sending_limit: StrictBool | None = None
    bounce_autopause_threshold: StrictStr | None = None
    out_of_office_detection_settings: OooSettingsModel | None = None
    ai_categorisation_options: list[StrictInt] | None = None
    domain_level_rate_limit: StrictBool | None = None
    add_unsubscribe_tag: StrictBool | None = None  # in Smartlead docs examples

    @model_validator(mode="after")
    def _require_any_field(self) -> "CampaignUpdateBodyModel":
        if not self.model_dump(exclude_none=True):
            raise ValueError("campaign update body must include at least one field")
        return self


class CampaignScheduleBodyModel(CliSchemaModel):
    cli_label = "campaign schedule body"

    timezone: StrictStr | None = None
    days_of_the_week: list[StrictInt] | None = None
    start_hour: StrictStr | None = None
    end_hour: StrictStr | None = None
    min_time_btw_emails: StrictInt | None = Field(default=None, ge=0)
    max_new_leads_per_day: StrictInt | None = Field(default=None, ge=0)
    schedule_start_time: StrictStr | None = None

    @field_validator("days_of_the_week")
    @classmethod
    def _validate_days(cls, value: list[int] | None) -> list[int] | None:
        if value is None:
            return value
        for i, day in enumerate(value):
            if day < 0 or day > 6:
                raise ValueError(f"days_of_the_week[{i}] must be 0..6")
        return value

    @model_validator(mode="after")
    def _require_any_field(self) -> "CampaignScheduleBodyModel":
        if not self.model_dump(exclude_none=True):
            raise ValueError("campaign schedule body must include at least one field")
        return self


class LeadInputModel(CliSchemaModel):
    cli_label = "lead input"

    first_name: StrictStr | None = None
    last_name: StrictStr | None = None
    email: StrictStr | None = None
    phone_number: StrictStr | StrictInt | float | None = None
    company_name: StrictStr | None = None
    website: StrictStr | None = None
    location: StrictStr | None = None
    custom_fields: dict[str, Any] | None = None
    linkedin_profile: StrictStr | None = None
    company_url: StrictStr | None = None


class CampaignLeadsAddSettingsModel(CliSchemaModel):
    cli_label = "campaign leads add body.settings"

    ignore_global_block_list: StrictBool | None = None
    ignore_unsubscribe_list: StrictBool | None = None
    ignore_community_bounce_list: StrictBool | None = None
    ignore_duplicate_leads_in_other_campaign: StrictBool | None = None
    ignore_duplicate_leads_in_same_campaign: StrictBool | None = None
    ignore_invalid_emails: StrictBool | None = None


class CampaignLeadsAddBodyModel(CliSchemaModel):
    cli_label = "campaign leads add body"

    lead_list: list[LeadInputModel]
    settings: CampaignLeadsAddSettingsModel | None = None

    @field_validator("lead_list")
    @classmethod
    def _validate_lead_list_nonempty(cls, value: list[LeadInputModel]) -> list[LeadInputModel]:
        if not value:
            raise ValueError("lead_list must not be empty")
        for i, lead in enumerate(value):
            if lead.email is None or lead.email == "":
                raise ValueError(f"lead_list[{i}].email is required")
        return value


class CampaignLeadUpdateBodyModel(LeadInputModel):
    cli_label = "campaign lead update body"
    email: StrictStr

    @model_validator(mode="after")
    def _require_any_field(self) -> "CampaignLeadUpdateBodyModel":
        if not self.model_dump(exclude_none=True):
            raise ValueError("campaign lead update body must include at least one field")
        return self


class CampaignWebhookUpsertBodyModel(CliSchemaModel):
    cli_label = "campaign webhook upsert body"

    id: StrictInt | None = None
    name: StrictStr
    webhook_url: StrictStr
    event_types: list[StrictStr]
    categories: list[StrictStr] | None = None

    @field_validator("event_types")
    @classmethod
    def _validate_event_types_nonempty(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("event_types must not be empty")
        return value
