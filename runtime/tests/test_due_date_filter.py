from __future__ import annotations

import logging
import unittest
from datetime import date

from prumo_runtime.workspace import (
    filter_by_due_date,
    is_item_visible_today,
    parse_cobrar_date,
)


class ParseCobrarDateTests(unittest.TestCase):
    """Parser do marker `| cobrar: DD/MM` nos itens da PAUTA.

    Convenção viva do usuário. Dois formatos aceitos:
    - `| cobrar: 23/04` (dia/mês, ano implícito = ano atual)
    - `| cobrar: 05/01/2027` (explícito, pra datas além do ano corrente)
    """

    def test_returns_none_when_no_marker(self) -> None:
        self.assertIsNone(parse_cobrar_date("- Fazer X", today=date(2026, 4, 22)))

    def test_parses_short_form_dd_mm(self) -> None:
        result = parse_cobrar_date(
            "- Cancelar Folha | cobrar: 30/04",
            today=date(2026, 4, 22),
        )
        self.assertEqual(result, date(2026, 4, 30))

    def test_parses_long_form_dd_mm_yyyy(self) -> None:
        result = parse_cobrar_date(
            "- Renovar seguro | cobrar: 05/01/2027",
            today=date(2026, 4, 22),
        )
        self.assertEqual(result, date(2027, 1, 5))

    def test_short_form_wraps_to_next_year_if_date_already_passed_by_months(self) -> None:
        # Item com "| cobrar: 05/01" escrito em abril/2026. O usuário quis dizer
        # "5 de janeiro do PRÓXIMO ano" porque 5 de janeiro de 2026 já passou há
        # meses. Heurística: se a data com ano atual cai mais de 60 dias no
        # passado, assume ano seguinte.
        result = parse_cobrar_date(
            "- Renovar domínio | cobrar: 05/01",
            today=date(2026, 4, 22),
        )
        self.assertEqual(result, date(2027, 1, 5))

    def test_short_form_keeps_current_year_if_date_recently_passed(self) -> None:
        # Item com "| cobrar: 15/04" escrito em 22/04. O usuário esqueceu, tá
        # atrasado — NÃO quer dizer "15 de abril de 2027". Mantém ano atual.
        result = parse_cobrar_date(
            "- Ligar pro contador | cobrar: 15/04",
            today=date(2026, 4, 22),
        )
        self.assertEqual(result, date(2026, 4, 15))

    def test_malformed_date_returns_none_and_logs_warning(self) -> None:
        with self.assertLogs("prumo_runtime.workspace", level="WARNING") as cm:
            result = parse_cobrar_date(
                "- Item bagunçado | cobrar: amanhã",
                today=date(2026, 4, 22),
            )
        self.assertIsNone(result)
        self.assertTrue(any("cobrar" in msg for msg in cm.output))

    def test_marker_with_extra_whitespace(self) -> None:
        result = parse_cobrar_date(
            "- Item | cobrar:   30/04  ",
            today=date(2026, 4, 22),
        )
        self.assertEqual(result, date(2026, 4, 30))

    def test_invalid_month_returns_none(self) -> None:
        # 30/13 não existe. Não deve virar data, não deve crashar.
        with self.assertLogs("prumo_runtime.workspace", level="WARNING"):
            result = parse_cobrar_date(
                "- Item errado | cobrar: 30/13",
                today=date(2026, 4, 22),
            )
        self.assertIsNone(result)


class IsItemVisibleTodayTests(unittest.TestCase):
    """Regra do filtro temporal.

    Item com `cobrar: D` fica oculto do dia atual até D-2.
    Aparece em D-1 (véspera) e D (dia). Também aparece em D+1, D+2... (atrasado).
    Item sem marker aparece sempre.
    """

    def test_item_without_marker_always_visible(self) -> None:
        self.assertTrue(
            is_item_visible_today("- Item comum", today=date(2026, 4, 22))
        )

    def test_item_cobrar_future_is_hidden(self) -> None:
        # cobrar: 30/04, hoje 22/04 — 8 dias no futuro, esconde.
        self.assertFalse(
            is_item_visible_today(
                "- Cancelar Folha | cobrar: 30/04",
                today=date(2026, 4, 22),
            )
        )

    def test_item_cobrar_tomorrow_is_visible(self) -> None:
        # cobrar: 23/04, hoje 22/04 — D-1, deve aparecer (véspera).
        self.assertTrue(
            is_item_visible_today(
                "- Reunião Sonia | cobrar: 23/04",
                today=date(2026, 4, 22),
            )
        )

    def test_item_cobrar_today_is_visible(self) -> None:
        # cobrar: 22/04, hoje 22/04 — D, aparece.
        self.assertTrue(
            is_item_visible_today(
                "- Entregar relatório | cobrar: 22/04",
                today=date(2026, 4, 22),
            )
        )

    def test_item_cobrar_in_past_is_visible_because_overdue(self) -> None:
        # cobrar: 15/04, hoje 22/04 — atrasado 7 dias, precisa aparecer.
        self.assertTrue(
            is_item_visible_today(
                "- Ligar pro contador | cobrar: 15/04",
                today=date(2026, 4, 22),
            )
        )

    def test_item_cobrar_far_future_year_hidden(self) -> None:
        # cobrar: 05/01/2027, hoje 22/04/2026 — longe, esconde.
        self.assertFalse(
            is_item_visible_today(
                "- Renovar seguro | cobrar: 05/01/2027",
                today=date(2026, 4, 22),
            )
        )

    def test_malformed_marker_item_stays_visible(self) -> None:
        # Marker quebrado não pode fazer item sumir — fail-open.
        with self.assertLogs("prumo_runtime.workspace", level="WARNING"):
            self.assertTrue(
                is_item_visible_today(
                    "- Item bagunçado | cobrar: amanhã",
                    today=date(2026, 4, 22),
                )
            )


class FilterByDueDateTests(unittest.TestCase):
    """Aplica o filtro na lista inteira.

    Preserva ordem original. Itens sem marker e itens já devidos passam.
    Itens com cobrar futuro caem.
    """

    def test_empty_list(self) -> None:
        self.assertEqual(filter_by_due_date([], today=date(2026, 4, 22)), [])

    def test_mixed_list_keeps_due_and_marker_free(self) -> None:
        items = [
            "- Sem marker",
            "- Reunião amanhã | cobrar: 23/04",
            "- Cancelar Folha | cobrar: 30/04",
            "- Ligar contador | cobrar: 15/04",
            "- Renovar seguro | cobrar: 05/01/2027",
        ]
        filtered = filter_by_due_date(items, today=date(2026, 4, 22))
        self.assertEqual(
            filtered,
            [
                "- Sem marker",
                "- Reunião amanhã | cobrar: 23/04",
                "- Ligar contador | cobrar: 15/04",
            ],
        )

    def test_all_hidden_returns_empty(self) -> None:
        items = [
            "- A | cobrar: 25/04",
            "- B | cobrar: 26/04",
        ]
        self.assertEqual(
            filter_by_due_date(items, today=date(2026, 4, 22)),
            [],
        )


if __name__ == "__main__":
    logging.disable(logging.CRITICAL)
    unittest.main()
