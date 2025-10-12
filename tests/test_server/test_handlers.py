import mcp.types as types
import pytest

from governmentreporter.apis.base import Document as ApiDocument
from governmentreporter.database.qdrant import Document as QdrantDocument
from governmentreporter.server.mcp_server import GovernmentReporterMCP


class _FakeQdrantClient:
    """Simple stub used to satisfy handler dependencies in tests."""

    def __init__(self, document: QdrantDocument):
        self._document = document

    def get_document(self, document_id: str, collection_name: str) -> QdrantDocument:
        return self._document

    def list_collections(self) -> list[str]:
        return ["executive_orders"]


@pytest.mark.asyncio
async def test_handle_get_document_by_id_returns_full_executive_order(monkeypatch):
    from governmentreporter.server.handlers import handle_get_document_by_id

    qdrant_doc = QdrantDocument(
        id="eo_chunk_1",
        text="Chunk excerpt text.",
        embedding=[0.0],
        metadata={
            "document_number": "2024-12345",
            "title": "Strengthening Example Infrastructure",
            "executive_order_number": "14099",
            "president": "Doe",
            "signing_date": 1711944000,  # 2024-04-01 as Unix timestamp
        },
    )

    api_document = ApiDocument(
        id="2024-12345",
        title="Strengthening Example Infrastructure",
        date="2024-04-01",
        type="Executive Order",
        source="Federal Register",
        content="Full executive order text for testing purposes.",
        metadata={
            "executive_order_number": "14099",
            "president": {"name": "Jane Doe"},
            "signing_date": 1711944000,  # 2024-04-01 as Unix timestamp
        },
        url="https://example.com/eo/14099",
    )

    class _StubFederalRegisterClient:
        def __init__(self):
            pass

        def get_document(self, document_id: str) -> ApiDocument:
            assert document_id == "2024-12345"
            return api_document

    monkeypatch.setattr(
        "governmentreporter.server.handlers.FederalRegisterClient",
        _StubFederalRegisterClient,
    )

    response = await handle_get_document_by_id(
        _FakeQdrantClient(qdrant_doc),
        {
            "document_id": "eo_chunk_1",
            "collection": "executive_orders",
            "full_document": True,
        },
    )

    assert "### Full Order Text" in response
    assert "Full executive order text for testing purposes." in response
    assert "**President:** Jane Doe" in response


@pytest.mark.asyncio
async def test_call_tool_returns_call_tool_result(monkeypatch):
    qdrant_doc = QdrantDocument(
        id="eo_chunk_1",
        text="Chunk excerpt text.",
        embedding=[0.0],
        metadata={
            "document_number": "2024-12345",
            "title": "Strengthening Example Infrastructure",
            "executive_order_number": "14099",
            "president": "Doe",
            "signing_date": 1711944000,  # 2024-04-01 as Unix timestamp
        },
    )

    server = GovernmentReporterMCP()
    server.qdrant_client = _FakeQdrantClient(qdrant_doc)

    call_request = types.CallToolRequest(
        params=types.CallToolRequestParams(
            name="get_document_by_id",
            arguments={
                "document_id": "eo_chunk_1",
                "collection": "executive_orders",
                "full_document": False,
            },
        )
    )

    handler = server.server.request_handlers[types.CallToolRequest]
    server_result = await handler(call_request)

    assert isinstance(server_result.root, types.CallToolResult)
    assert not server_result.root.isError
    assert server_result.root.content
    text_blocks = [
        block
        for block in server_result.root.content
        if isinstance(block, types.TextContent)
    ]
    assert text_blocks, "Expected text content in CallToolResult."
    assert any("Document Retrieved" in block.text for block in text_blocks)
