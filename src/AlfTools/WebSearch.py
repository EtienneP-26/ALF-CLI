__all__ = ["web_search"]

from ddgs import DDGS

def web_search(
    question: str,
    # max_results: int = 5,
    region: str = "us-en",
    timelimit: str | None = None,
) -> list[dict[str, str]]:
    """Makes a research on the web using duckduckgo with a question

    :param question: the research question
    :param region: where the region of the search. default us-en
    :param timelimit: Time constraint: d (day), w (week), m (month), y (year). default None
    :returns: the command: the search result with max_results results
    """
    # :param max_results: results number of pages. default 5
    
    try:
        with DDGS() as ddgs:
            resultats = ddgs.text(question, max_results=5, region=region, timelimit=timelimit)
    except Exception as e:
        return [{"Error": f"Search failed: {e}"}]

    if not resultats:
        return [{"Error": "No relevant result found on the web."}]

    return resultats
