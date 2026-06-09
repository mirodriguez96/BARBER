from barberia.routers import set_current_db_name


class PaginationTestMixin:
    """
    Reusable pagination tests for dashboard list views.

    Subclasses must provide:
        section_name: str  — e.g. "barbers", "catalog", "sales"
        context_key: str   — e.g. "people_page", "catalog_items", "sales"
        _create_pagination_items(count): method to create test records

    Subclasses need setUp with:
        self.client (logged in as admin)
        self.url (reverse('dashboard:home'))
        set_current_db_name(None)
    """

    section_name = ""
    context_key = ""
    page_size = 10

    def _get_list_url(self, page=None, **extra):
        params = [f"section={self.section_name}"]
        if page is not None:
            params.append(f"page={page}")
        for k, v in extra.items():
            params.append(f"{k}={v}")
        return f"{self.url}?{'&'.join(params)}"

    def _get_pagination_page(self, page=None, **extra):
        url = self._get_list_url(page=page, **extra)
        set_current_db_name(None)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        return response.context[self.context_key]

    def _get_item_id(self, item):
        return item.pk

    def test_page_1_shows_page_size(self):
        self._create_pagination_items(self.page_size + 1)
        page = self._get_pagination_page(page=1)
        self.assertEqual(len(list(page.object_list)), self.page_size)

    def test_page_2_shows_remaining(self):
        self._create_pagination_items(self.page_size + 1)
        page = self._get_pagination_page(page=2)
        self.assertEqual(len(list(page.object_list)), 1)

    def test_no_duplicates_across_pages(self):
        self._create_pagination_items(15)
        p1 = self._get_pagination_page(page=1)
        p2 = self._get_pagination_page(page=2)
        ids_p1 = {self._get_item_id(item) for item in p1.object_list}
        ids_p2 = {self._get_item_id(item) for item in p2.object_list}
        self.assertFalse(ids_p1 & ids_p2)

    def test_invalid_page_returns_first_page(self):
        self._create_pagination_items(self.page_size + 1)
        page = self._get_pagination_page(page="abc")
        self.assertEqual(len(list(page.object_list)), self.page_size)
        self.assertEqual(page.number, 1)

    def test_negative_page_returns_last_page(self):
        self._create_pagination_items(self.page_size + 1)
        page = self._get_pagination_page(page="-1")
        self.assertEqual(len(list(page.object_list)), 1)
        self.assertEqual(page.number, page.paginator.num_pages)

    def test_page_too_high_returns_last_page(self):
        self._create_pagination_items(self.page_size + 1)
        page = self._get_pagination_page(page="999")
        self.assertEqual(len(list(page.object_list)), 1)
        self.assertEqual(page.number, page.paginator.num_pages)
