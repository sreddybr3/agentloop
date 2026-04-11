"""ADK entry point — exposes the root agent for `adk run` and `adk web`.

Google ADK expects a module-level `root_agent` (or an `agent` variable)
in the package's agent.py file.
"""

from doc_search_with_reranking_validation.root_agent import root_agent  # noqa: F401