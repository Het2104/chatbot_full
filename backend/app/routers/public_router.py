"""
Public Router

Unauthenticated endpoints used by the embeddable widget.

Endpoints:
    GET /public/chatbot/{embed_key}   — returns widget config JSON (no auth)
    GET /widget/{embed_key}.js        — returns the self-contained embed script (no auth)
"""

import os
import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import get_db
from app.models.chatbot import Chatbot

logger = logging.getLogger(__name__)

router = APIRouter()

# The URL of the Next.js frontend — used inside the generated widget JS.
# Override via FRONTEND_URL env var in production.
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")


# ---------------------------------------------------------------------------
# Response schema
# ---------------------------------------------------------------------------

class PublicChatbotConfig(BaseModel):
    chatbot_id: int
    name: str
    widget_color: str
    widget_welcome_message: str
    widget_position: str

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# GET /public/chatbot/{embed_key}
# ---------------------------------------------------------------------------

@router.get("/public/chatbot/{embed_key}", response_model=PublicChatbotConfig)
def get_public_chatbot_config(embed_key: str, db: Session = Depends(get_db)):
    """
    Return the public widget configuration for a chatbot identified by its embed key.

    This endpoint is intentionally unauthenticated — it exposes only the data
    needed to render the widget on a third-party website.

    Path parameters:
        embed_key: UUID embed key assigned to the chatbot

    Returns:
        { chatbot_id, name, widget_color, widget_welcome_message, widget_position }

    Raises:
        404: If no chatbot has this embed key
    """
    chatbot = db.query(Chatbot).filter(Chatbot.embed_key == embed_key).first()
    if not chatbot:
        raise HTTPException(status_code=404, detail="Chatbot not found for this embed key")

    return PublicChatbotConfig(
        chatbot_id=chatbot.id,
        name=chatbot.name,
        widget_color=chatbot.widget_color,
        widget_welcome_message=chatbot.widget_welcome_message,
        widget_position=chatbot.widget_position,
    )


# ---------------------------------------------------------------------------
# GET /widget/{embed_key}.js
# ---------------------------------------------------------------------------

@router.get("/widget/{embed_key}.js")
def get_widget_script(embed_key: str, db: Session = Depends(get_db)):
    """
    Return a self-contained JavaScript snippet that renders a floating chat bubble.

    Website owners include this as:
        <script src="https://yourapi.com/widget/EMBED_KEY.js"></script>

    The script:
    1. Fetches widget config from /public/chatbot/{embed_key}
    2. Creates a floating circular button styled with widget_color
    3. On click, toggles a popup iframe pointing to {FRONTEND_URL}/embed/{embed_key}
    4. Positions the bubble per widget_position (bottom-right / bottom-left)

    Path parameters:
        embed_key: UUID embed key assigned to the chatbot

    Returns:
        Content-Type: application/javascript

    Raises:
        404: If no chatbot has this embed key
    """
    chatbot = db.query(Chatbot).filter(Chatbot.embed_key == embed_key).first()
    if not chatbot:
        raise HTTPException(status_code=404, detail="Chatbot not found for this embed key")

    color = chatbot.widget_color.replace('"', '\\"')
    position = chatbot.widget_position  # "bottom-right" or "bottom-left"
    frontend_url = FRONTEND_URL.rstrip("/")

    horiz_prop = "right" if position == "bottom-right" else "left"

    js = f"""
(function() {{
  if (window.__chatbotWidgetLoaded_{embed_key[:8]}) return;
  window.__chatbotWidgetLoaded_{embed_key[:8]} = true;

  var EMBED_KEY = "{embed_key}";
  var COLOR     = "{color}";
  var FRONTEND  = "{frontend_url}";
  var HORIZ     = "{horiz_prop}";

  /* ---- floating button ---- */
  var btn = document.createElement("button");
  btn.id = "chatbot-widget-btn-" + EMBED_KEY;
  btn.innerHTML = "&#128172;"; /* speech bubble emoji */
  btn.title = "Chat with us";
  Object.assign(btn.style, {{
    position:     "fixed",
    bottom:       "24px",
    [HORIZ]:      "24px",
    zIndex:       "2147483647",
    width:        "56px",
    height:       "56px",
    borderRadius: "50%",
    background:   COLOR,
    color:        "#fff",
    border:       "none",
    cursor:       "pointer",
    fontSize:     "24px",
    boxShadow:    "0 4px 16px rgba(0,0,0,0.25)",
    display:      "flex",
    alignItems:   "center",
    justifyContent: "center",
    lineHeight:   "1",
    padding:      "0",
  }});

  /* ---- iframe container ---- */
  var container = document.createElement("div");
  container.id = "chatbot-widget-container-" + EMBED_KEY;
  Object.assign(container.style, {{
    position:     "fixed",
    bottom:       "92px",
    [HORIZ]:      "16px",
    zIndex:       "2147483646",
    width:        "380px",
    height:       "580px",
    borderRadius: "16px",
    overflow:     "hidden",
    boxShadow:    "0 8px 32px rgba(0,0,0,0.22)",
    display:      "none",
    border:       "none",
  }});

  var iframe = document.createElement("iframe");
  iframe.src = FRONTEND + "/embed/" + EMBED_KEY;
  iframe.title = "Chat";
  Object.assign(iframe.style, {{
    width:    "100%",
    height:   "100%",
    border:   "none",
  }});
  iframe.setAttribute("allow", "clipboard-write");

  container.appendChild(iframe);

  /* ---- toggle logic ---- */
  var open = false;
  btn.addEventListener("click", function() {{
    open = !open;
    container.style.display = open ? "block" : "none";
    btn.innerHTML = open ? "&#10005;" : "&#128172;";
  }});

  document.body.appendChild(container);
  document.body.appendChild(btn);
}})();
""".strip()

    return Response(
        content=js,
        media_type="application/javascript",
        headers={
            # Cache for 5 minutes in browser, 1 hour on CDN
            "Cache-Control": "public, max-age=300, s-maxage=3600",
        },
    )
