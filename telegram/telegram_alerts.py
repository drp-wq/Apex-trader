"""
Informational Telegram Alert Dispatcher for APEX TRADER.
Read-only event notifier. Never processes commands or initiates trade execution.
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any
import requests
import logging
from models.domain import SignalDirection, Provenance
from analysis.setup_engine import TradeSetup
from paper.paper_engine import PaperTradeRecord

logger = logging.getLogger(__name__)


class TelegramNotifier:
    def __init__(
        self,
        bot_token: Optional[str] = None,
        chat_id: Optional[str] = None,
        enabled: bool = False
    ):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.enabled = enabled and bool(bot_token and chat_id)

    def send_message(self, text: str) -> bool:
        """Sends raw markdown message to Telegram channel/group."""
        if not self.enabled:
            logger.info(f"[TELEGRAM_MOCK_DISPATCH]: {text}")
            return True

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "Markdown"
        }
        try:
            resp = requests.post(url, json=payload, timeout=5)
            return resp.status_code == 200
        except Exception as err:
            logger.error(f"Failed to send Telegram alert: {err}")
            return False

    def notify_new_setup(self, setup: TradeSetup) -> bool:
        """Formats and dispatches a NEW_SETUP notification."""
        side = "🟢 LONG" if setup.direction == SignalDirection.BUY else "🔴 SHORT"
        msg = (
            f"⚡ *APEX TRADER — SETUP DETECTED* ⚡\n"
            f"*Symbol:* `{setup.symbol}` ({setup.provenance.value})\n"
            f"*Direction:* {side}\n"
            f"*Entry Price:* `{setup.entry_price}`\n"
            f"*Stop Loss:* `{setup.stop_loss}`\n"
            f"*TP1 (1:2):* `{setup.tp1}`\n"
            f"*TP2 (1:3):* `{setup.tp2}`\n"
            f"*TP3 (1:5):* `{setup.tp3}`\n"
            f"*Confluence Score:* `{setup.score}/100`\n"
            f"*Confidence:* `{int(setup.confidence * 100)}%`\n"
            f"*Reasons:* {', '.join(setup.reasons[:2])}\n"
            f"_Mode: PAPER ONLY — NO REAL CAPITAL AT RISK_"
        )
        return self.send_message(msg)

    def notify_paper_fill(self, symbol: str, direction: SignalDirection, price: float, qty: float) -> bool:
        """Formats and dispatches a PAPER_ENTRY notification."""
        side = "LONG" if direction == SignalDirection.BUY else "SHORT"
        msg = (
            f"📋 *PAPER TRADE EXECUTED*\n"
            f"*Symbol:* `{symbol}`\n"
            f"*Side:* `{side}`\n"
            f"*Exec Price:* `${price}`\n"
            f"*Quantity:* `{qty}`\n"
            f"_Safety: DRY_RUN Active_"
        )
        return self.send_message(msg)

    def notify_trade_closed(self, record: PaperTradeRecord) -> bool:
        """Formats and dispatches a PAPER_EXIT notification."""
        pnl_icon = "🟢" if record.realized_pnl >= 0 else "🔴"
        msg = (
            f"{pnl_icon} *PAPER POSITION CLOSED*\n"
            f"*Symbol:* `{record.symbol}`\n"
            f"*Exit Reason:* `{record.exit_reason}`\n"
            f"*Net PnL:* `${record.realized_pnl}`\n"
            f"*Fees:* `${record.fees_paid}`\n"
            f"*Exit Price:* `${record.exit_price}`"
        )
        return self.send_message(msg)

    def notify_emergency_flatten(self, count: int) -> bool:
        """Dispatches an EMERGENCY_FLATTEN alert."""
        msg = (
            f"🚨 *EMERGENCY FLATTEN TRIGGERED* 🚨\n"
            f"Liquidated `{count}` active paper position(s).\n"
            f"All pending simulated orders purged."
        )
        return self.send_message(msg)
