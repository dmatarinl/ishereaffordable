from app.food.basket import canonical_food_basket, load_food_basket


def test_canonical_food_basket_has_expected_mvp_shape() -> None:
    basket = canonical_food_basket()

    assert basket.version == "2026-06-spain-single-adult-v1"
    assert basket.currency == "EUR"
    assert basket.period == "month"
    assert basket.aggregation_method == "median_valid_supermarket_basket"
    assert 30 <= len(basket.items) <= 50
    assert basket.required_item_count >= 25
    assert basket.optional_item_count > 0
    assert basket.seed_monthly_total_eur() > 200


def test_food_basket_items_are_matchable_and_unique() -> None:
    basket = load_food_basket()
    item_ids = [item.id for item in basket.items]

    assert len(item_ids) == len(set(item_ids))
    assert all(item.reference_terms for item in basket.items)
    assert all(item.seed_unit_price_eur >= 0 for item in basket.items)


def test_food_basket_declares_sources_and_confidence_rules() -> None:
    basket = canonical_food_basket()
    source_names = {source.name for source in basket.source_basis}

    assert "MAPA Panel de Consumo Alimentario" in source_names
    assert "INE Encuesta de Presupuestos Familiares" in source_names
    assert "AESAN Recomendaciones dieteticas y de actividad fisica" in source_names
    assert basket.confidence_thresholds["high"].minimum_product_coverage == 0.9
    assert basket.confidence_thresholds["high"].minimum_valid_sources == 2
    assert basket.confidence_thresholds["medium"].minimum_product_coverage == 0.75
