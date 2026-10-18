"""Read-only view of the whole repository, including pre-V2 saved records."""

from services.ingestion import InvalidReelUrl, canonicalize_reel_url
from services.organization import annotate_item

ITEM_FIELDS = "id,video_id,title,summary,key_ideas,repositories,concepts,action_items,tags,raw_extraction,source_url,created_at"
VIDEO_FIELDS = "id,instagram_url,canonical_url,video_created_at,processed_at,status,transcript,caption,raw_extraction"
TOOL_FIELDS = "id,name,functionality,problem_solved,tags,first_seen_date,source_video_ids"


class RepositoryError(Exception):
    pass


def _rows(db, table: str, columns: str, keys=("id",)) -> list[dict]:
    collected = {}
    for offset in range(0, 1_000_000, 200):
        query = db.table(table).select(columns)
        for key in keys:
            query = query.order(key)
        batch = query.range(offset, offset + 199).execute().data or []
        previous = len(collected)
        for row in batch:
            collected[tuple(row.get(key) for key in keys)] = row
        if len(batch) < 200:
            return list(collected.values())
        if len(collected) == previous:
            raise RepositoryError("Repository pagination did not advance.")
    raise RepositoryError("Repository pagination limit reached.")


def _extraction(value) -> dict:
    return value if isinstance(value, dict) else {"tools": value if isinstance(value, list) else []}


def _canonical(url: str) -> str:
    try:
        return canonicalize_reel_url(url)
    except InvalidReelUrl:
        return url.split("?", 1)[0].rstrip("/")


def load_repository(db) -> list[dict]:
    items = [annotate_item(item) for item in _rows(db, "knowledge_items", ITEM_FIELDS)]
    knowledge_by_video = {item.get("video_id"):item for item in items}
    videos = _rows(db, "videos", VIDEO_FIELDS)
    tools = _rows(db, "tools", TOOL_FIELDS)
    interactions = _rows(db, "user_interactions", "id,tool_id,status,notes")
    links = _rows(db, "video_tools", "video_id,tool_id", ("video_id", "tool_id"))
    by_video = {video["id"]: video for video in videos}
    by_tool = {tool["id"]: tool for tool in tools}
    by_interaction = {row["tool_id"]: row for row in interactions}
    tool_videos = {tool["id"]: set(tool.get("source_video_ids") or []) for tool in tools}
    for link in links:
        tool_videos.setdefault(link["tool_id"], set()).add(link["video_id"])
    video_tools = {}
    for tool_id, video_ids in tool_videos.items():
        for video_id in video_ids:
            if tool_id in by_tool:
                video_tools.setdefault(video_id, []).append(by_tool[tool_id])

    def tool_context(tool):
        interaction = by_interaction.get(tool["id"], {})
        return {
            "name": tool.get("name"), "functionality": tool.get("functionality"),
            "problem_solved": tool.get("problem_solved"), "tags": tool.get("tags") or [],
            "status": interaction.get("status") or "to_explore", "notes": interaction.get("notes") or "",
        }

    content, covered = [], set()
    for item in items:
        video = by_video.get(item.get("video_id"), {})
        covered.add(item.get("video_id"))
        content.append({
            **item, "kind": "item", "video_id": item.get("video_id"),
            "saved_at": video.get("processed_at") or item.get("created_at") or "",
            "published_on": video.get("video_created_at"), "processing_status": video.get("status") or "completed",
            "transcript": video.get("transcript") or "", "caption": video.get("caption") or "",
            "related_tools": [tool_context(tool) for tool in video_tools.get(item.get("video_id"), [])],
        })
    for video in videos:
        if video["id"] in covered:
            continue
        extraction = _extraction(video.get("raw_extraction"))
        associated = video_tools.get(video["id"], [])
        extracted_tools = [tool for tool in extraction.get("tools", []) if isinstance(tool, dict)]
        names = [tool.get("name") for tool in associated or extracted_tools if tool.get("name")]
        caption = video.get("caption") or ""
        title = extraction.get("title") or ", ".join(names) or caption.split("\n")[0][:140] or "Saved Reel (content not processed)"
        content.append({
            **extraction, "id": "video:" + video["id"], "kind": "video", "video_id": video["id"],
            "title": title, "summary": extraction.get("summary") or "",
            "source_url": video.get("canonical_url") or video.get("instagram_url") or "",
            "saved_at": video.get("processed_at") or "", "published_on": video.get("video_created_at"),
            "processing_status": video.get("status"), "transcript": video.get("transcript") or "",
            "caption": caption, "raw_extraction": extraction,
            "related_tools": [tool_context(tool) for tool in associated],
        })

    # Historical URL variants should not fill a latest-N recommendation.
    unique = {}
    for source in content:
        key = _canonical(source.get("source_url") or "") or source["id"]
        existing = unique.get(key)
        if existing is None:
            unique[key] = source
            continue
        preferred, other = (source, existing) if source["kind"] == "item" else (existing, source)
        for field in ("transcript", "caption"):
            preferred[field] = "\n\n".join(dict.fromkeys(text for text in (preferred.get(field), other.get(field)) if text))
        preferred["related_tools"] += [tool for tool in other.get("related_tools", []) if tool not in preferred["related_tools"]]
        dates = [value for value in (preferred.get("saved_at"), other.get("saved_at")) if value]
        preferred["saved_at"] = min(dates) if dates else ""
        unique[key] = preferred

    sources = list(unique.values())
    for tool in tools:
        linked = [by_video[video_id] for video_id in tool_videos.get(tool["id"], set()) if video_id in by_video]
        linked.sort(key=lambda row: (row.get("processed_at") or "", row["id"]), reverse=True)
        source_video = linked[0] if linked else {}
        context = tool_context(tool)
        linked_knowledge = [knowledge_by_video[video_id] for video_id in tool_videos.get(tool["id"], set()) if video_id in knowledge_by_video]
        review_reasons = list(dict.fromkeys(reason for item in linked_knowledge for reason in item.get("review_reasons", [])))
        topics = {topic["id"]:topic for item in linked_knowledge for topic in item.get("topics", [])}
        sources.append({
            "id": "tool:" + tool["id"], "kind": "tool", "title": tool.get("name") or "Unnamed tool",
            "summary": tool.get("functionality") or "", "key_ideas": [tool.get("problem_solved") or ""],
            "tags": tool.get("tags") or [], "status": context["status"], "notes": context["notes"],
            "saved_at": tool.get("first_seen_date") or "", "published_on": None,
            "source_url": source_video.get("canonical_url") or source_video.get("instagram_url") or "",
            "video_id": source_video.get("id"),
            "review_reasons": review_reasons, "topics": list(topics.values()),
        })
    sources.sort(key=lambda row: (str(row.get("saved_at") or ""), row["id"]), reverse=True)
    return sources
