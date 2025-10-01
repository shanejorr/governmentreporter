GovernmentReporter Documentation
==================================

Welcome to GovernmentReporter, an MCP (Model Context Protocol) server that provides Large Language Models with semantic search capabilities over US federal government documents.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   overview
   installation
   quickstart
   architecture
   api/index
   cli
   mcp_server
   ingestion
   deployment
   troubleshooting
   contributing

Overview
--------

GovernmentReporter enables LLMs to search and retrieve information from:

* **Supreme Court Opinions**: Hierarchically chunked by opinion type, sections, and justices
* **Executive Orders**: Structured by header, sections, and subsections
* **Future**: Congressional documents, federal rules, and more

Key Features
~~~~~~~~~~~~

* **Hierarchical Chunking**: Intelligent document splitting by natural structure
* **Rich Metadata**: AI-extracted legal topics, citations, and policy information
* **Semantic Search**: Vector-based similarity search powered by Qdrant
* **MCP Integration**: Direct LLM access via Model Context Protocol
* **Resumable Ingestion**: Progress tracking for large-scale data processing
* **Production Ready**: Docker support, comprehensive logging, monitoring

Quick Links
-----------

* :doc:`installation` - Get started with GovernmentReporter
* :doc:`quickstart` - Run your first searches
* :doc:`api/index` - API reference documentation
* :doc:`mcp_server` - MCP server tools and usage
* :doc:`deployment` - Deploy in production
* :doc:`troubleshooting` - Common issues and solutions

Architecture
------------

.. code-block:: text

   ┌─────────────────────────────────────────────────────────────┐
   │                         LLM (Claude)                         │
   └───────────────────────────┬─────────────────────────────────┘
                               │ MCP Protocol
   ┌───────────────────────────▼─────────────────────────────────┐
   │                  GovernmentReporter MCP Server               │
   │  ┌──────────────┐  ┌──────────────┐  ┌───────────────────┐ │
   │  │   Handlers   │  │Query Processor│  │   Configuration   │ │
   │  └──────┬───────┘  └──────┬────────┘  └─────────────────── │ │
   └─────────┼──────────────────┼──────────────────────────────────┘
             │                  │
   ┌─────────▼──────────────────▼───────────────────────────────┐
   │                    Qdrant Vector Database                   │
   │         (Embeddings + Metadata + Chunks)                    │
   └──────────────────────────────────────────────────────────────┘
             ▲
             │ Ingestion Pipeline
   ┌─────────┴──────────────────────────────────────────────────┐
   │  Government APIs  →  Chunking  →  Embeddings  →  Storage   │
   │  (CourtListener, Federal Register, etc.)                    │
   └──────────────────────────────────────────────────────────────┘

Modules
-------

.. autosummary::
   :toctree: api
   :recursive:
   :caption: API Documentation

   governmentreporter.apis
   governmentreporter.database
   governmentreporter.processors
   governmentreporter.ingestion
   governmentreporter.server
   governmentreporter.cli
   governmentreporter.utils

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
