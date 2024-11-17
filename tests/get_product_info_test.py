import unittest
from main import get_product_info


class TestGetProductInfoIntegration(unittest.TestCase):

    def test_get_product_info_success(self):
        # URL товара
        product_url = "https://www.sp-computer.ru/catalog/smartfony/smartfon-xiaomi-redmi-14c-8-256gb-nfc-chernyy-ru/"

        # Ожидаемые данные
        expected_name = 'Смартфон Xiaomi Redmi 14C'
        expected_description = "Смартфон Xiaomi Redmi 14C"
        expected_price = "13490"

        result = get_product_info(product_url)

        self.assertIn(expected_name, result["name"])
        self.assertIn(expected_description, result["description"])
        self.assertEqual(result["price"], expected_price)

    def test_get_product_info_error(self):
        #невалидный URL
        invalid_url = "https://www.sp-computer.ru/nonexistent-product"
        result = get_product_info(invalid_url)
        self.assertIn("Ошибка получения данных", result["error"])


if __name__ == "__main__":
    unittest.main()