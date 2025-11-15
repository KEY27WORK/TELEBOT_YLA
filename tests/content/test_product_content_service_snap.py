# tests/content/test_product_content_service_snap.py
import pytest

@pytest.mark.asyncio
async def test_build_product_content_snapshot(content_service, dto_product, snapshot):
    dto = await content_service.build_product_content(
        product=dto_product,
        url="https://youngla.com/products/performance-tee",
        colors_text="• Black: S, M, L\n• White: 🚫",
    )

    # 1) Снимем снапшот целиком (как dict), чтобы дифф был наглядным
    snapshot.assert_match({
        "title": dto.title,
        "slogan": dto.slogan,
        "hashtags": dto.hashtags,
        "sections": dto.sections,
        "colors_text": dto.colors_text,
        "price_message": dto.price_message,
        "images": dto.images,
    })

    # 2) Мини-проверки инвариантов (не зависят от снапшота)
    assert isinstance(dto.images, list) and all(isinstance(x, str) for x in dto.images)
    assert dto.title and dto.price_message
