from typing import Optional

from offchain.metadata.fetchers.base_fetcher import BaseFetcher
from offchain.metadata.models.metadata import (
    Attribute,
    MediaDetails,
    Metadata,
    MetadataStandard,
)
from offchain.metadata.models.token import Token
from offchain.metadata.parsers.schema.schema_parser import SchemaParser
from offchain.metadata.registries.parser_registry import ParserRegistry


@ParserRegistry.register
class UnknownParser(SchemaParser):
    """A catch-all metadata parser that does a best effort pass at parsing metadata of any format.
    This parser should always be run last in the pipeline.
    """

    _METADATA_STANDARD: MetadataStandard = MetadataStandard.UNKNOWN

    def __init__(self, fetcher: BaseFetcher) -> None:
        self.fetcher = fetcher

    def get_name(self, raw_data: dict):
        if isinstance(raw_data.get("name"), str):
            return raw_data.get("name")
        return None

    def get_description(self, raw_data: dict):
        if isinstance(raw_data.get("description"), str):
            return raw_data.get("description")
        return None

    def get_attributes(self, raw_data: dict) -> list[Attribute]:
        attributes: list[Attribute] = []

        if isinstance(raw_data.get("properties"), dict):
            for key, value in raw_data["properties"].items():
                if isinstance(value, str):
                    attributes.append(Attribute(trait_type=key, value=value, display_type=None))
                elif isinstance(value, dict):
                    attributes.append(
                        Attribute(
                            trait_type=key,
                            value=value.get("description"),
                            display_type=value.get("type"),
                        )
                    )

        if isinstance(raw_data.get("attributes"), list):
            attributes += [
                Attribute(
                    trait_type=attribute.get("trait_type"),
                    value=attribute.get("value"),
                    display_type=attribute.get("display_type"),
                )
                for attribute in raw_data["attributes"]
            ]

        if isinstance(raw_data.get("traits"), list):
            attributes += [
                Attribute(
                    trait_type=attribute.get("trait_type"),
                    value=attribute.get("value"),
                    display_type=attribute.get("display_type"),
                )
                for attribute in raw_data["traits"]
            ]

        return attributes

    def get_image_uri(self, raw_data: dict):
        if isinstance(raw_data.get("image"), str):
            return raw_data["image"]
        if isinstance(raw_data.get("image_url"), str):
            return raw_data["image_url"]
        return None

    def get_image_details(self, raw_data: dict) -> Optional[MediaDetails]:
        image_uri = self.get_image_uri(raw_data=raw_data)
        if not image_uri:
            return None
        details = MediaDetails(uri=image_uri, size=None, sha256=None, mime=None)
        if isinstance(raw_data.get("image_details"), dict):
            details.size = raw_data["image_details"].get("size")
            details.sha256 = raw_data["image_details"].get("sha256")
            return details
        try:
            content_type, size = self.fetcher.fetch_mime_type_and_size(image_uri)
            details.mime_type = content_type
            details.size = size
        except Exception:
            pass
        return details

    def get_content_uri(self, raw_data: dict):
        if isinstance(raw_data.get("animation_url"), str):
            return raw_data["animation_url"]
        if isinstance(raw_data.get("animation"), str):
            return raw_data["animation"]
        return None

    def get_content_details(self, raw_data: dict) -> Optional[MediaDetails]:
        content_uri = self.get_content_uri(raw_data)
        if not content_uri:
            return None
        details = MediaDetails(uri=content_uri, size=None, sha256=None, mime=None)
        if isinstance(raw_data.get("animation_details"), dict):
            details.size = raw_data["animation_details"].get("size")
            details.sha256 = raw_data["animation_details"].get("sha256")
            return details
        try:
            content_type, size = self.fetcher.fetch_mime_type_and_size(content_uri)
            details.mime_type = content_type
            details.size = size
        except Exception:
            pass

        return details

    def parse_metadata(self, token: Token, raw_data: dict, *args, **kwargs) -> Optional[Metadata]:
        mime, _ = self.fetcher.fetch_mime_type_and_size(token.uri)

        return Metadata(
            token=token,
            raw_data=raw_data,
            standard=self._METADATA_STANDARD,
            attributes=self.get_attributes(raw_data=raw_data),
            name=self.get_name(raw_data=raw_data),
            description=self.get_description(raw_data=raw_data),
            mime_type=mime,
            image=self.get_image_details(raw_data=raw_data),
            content=self.get_content_details(raw_data=raw_data),
            additional_fields=[],
        )

    def should_parse_token(self, token: Token, raw_data: dict, *args, **kwargs) -> bool:
        return True
