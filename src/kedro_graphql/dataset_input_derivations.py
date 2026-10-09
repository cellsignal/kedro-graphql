"""Dataset input derivation rules and dependency validation."""

import re
from graphlib import CycleError, TopologicalSorter
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, field_validator, model_validator


def _validate_filename_suffix(value: str) -> str:
    if any(char in "/\\?#" or char.isspace() or ord(char) < 32 for char in value):
        raise ValueError("Suffixes must be nonempty filename suffixes")
    return value


class InputSuffixReplacement(BaseModel):
    model_config = ConfigDict(extra="forbid")
    from_suffix: str = Field(min_length=1)
    to_suffix: str = Field(min_length=1)

    @field_validator("from_suffix", "to_suffix")
    @classmethod
    def _validate_suffix(cls, value):
        return _validate_filename_suffix(value)


class InputRegexSubstitution(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pattern: str = Field(min_length=1)
    replacement: str

    @model_validator(mode="after")
    def _validate_expression(self):
        try:
            re.compile(self.pattern).sub(self.replacement, "")
        except (re.error, IndexError, OverflowError) as error:
            raise ValueError(f"Invalid Python regex substitution: {error}") from error
        return self


class DatasetInputDerivation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pipeline_name: str = Field(min_length=1)
    dataset_name: str = Field(min_length=1)
    source_dataset: str = Field(min_length=1)
    append_suffix: str | None = Field(default=None, min_length=1)
    replace_suffix: InputSuffixReplacement | None = None
    regex_sub: InputRegexSubstitution | None = None

    @field_validator("pipeline_name", "dataset_name", "source_dataset")
    @classmethod
    def _validate_name(cls, value):
        if not value.strip() or value != value.strip() or value.startswith("params:") or value == "parameters":
            raise ValueError("Derivation names must identify a pipeline or dataset without surrounding whitespace")
        return value

    @field_validator("append_suffix")
    @classmethod
    def _validate_suffix(cls, value):
        return _validate_filename_suffix(value) if value is not None else None

    @model_validator(mode="after")
    def _validate_operation(self):
        if sum(value is not None for value in (self.append_suffix, self.replace_suffix, self.regex_sub)) != 1:
            raise ValueError("Choose exactly one of append_suffix, replace_suffix, or regex_sub")
        return self


def validate_derivation_dependencies(
    registrations: list[DatasetInputDerivation],
) -> list[DatasetInputDerivation]:
    """Reject duplicate targets and cycles, then order rules by dependency."""
    targets = {(item.pipeline_name, item.dataset_name) for item in registrations}
    if len(targets) != len(registrations):
        raise ValueError("Duplicate dataset input derivation targets")
    for item in registrations:
        if item.dataset_name == item.source_dataset:
            raise ValueError("Dataset input derivations cannot reference themselves")
    by_target = {(item.pipeline_name, item.dataset_name): item for item in registrations}
    dependencies = {
        target: {(item.pipeline_name, item.source_dataset)} & targets
        for target, item in by_target.items()
    }
    try:
        return [by_target[target] for target in TopologicalSorter(dependencies).static_order()]
    except CycleError as error:
        raise ValueError("Dataset input derivations cannot contain cycles") from error


DerivationRegistrations = Annotated[
    list[DatasetInputDerivation], AfterValidator(validate_derivation_dependencies)
]


def validate_dataset_input_derivations(registrations: list[DatasetInputDerivation], pipelines):
    """Reject derivation registrations referring to unavailable graph datasets."""
    for item in registrations:
        if item.pipeline_name not in pipelines:
            raise ValueError(f"Unknown derivation pipeline: {item.pipeline_name}")
        pipeline = pipelines[item.pipeline_name]
        datasets = pipeline.all_inputs() | pipeline.all_outputs()
        if item.dataset_name not in datasets or item.source_dataset not in datasets:
            raise ValueError(f"Unknown derivation dataset for {item.pipeline_name}: {item.dataset_name} or {item.source_dataset}")
