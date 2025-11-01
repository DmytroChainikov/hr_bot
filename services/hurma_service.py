import datetime
from typing import Dict, Any, List, Optional
from urllib.parse import urlencode

import requests

from core.logger_settings import create_logger

logger = create_logger(__name__)


class HurmaService:
    """Сервісний клієнт для Hurma Public API v1"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        company: str = "yourcompany",
    ):
        """
        Ініціалізація клієнта Hurma API.

        Args:
            api_key: API ключ для автентифікації (старий метод)
            client_id: Client ID для OAuth
            client_secret: Client Secret для OAuth
            username: Email користувача для OAuth
            password: Пароль користувача для OAuth
            company: Назва компанії в Hurma (домен)
        """
        self.api_key = api_key
        self.client_id = client_id
        self.client_secret = client_secret
        self.username = username
        self.password = password
        self.company = company
        self.base_url = f"https://{company}.hurma.work/api/v3"
        self.__oauth_token = None

        # Визначаємо метод автентифікації
        if client_id and client_secret and username and password:
            # Використовуємо OAuth
            self._authenticate_oauth()
            print("OAuth authentication successful")
            self.headers = {
                "Authorization": f"Bearer {self.__oauth_token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        # elif api_key:
        #     # Використовуємо API ключ
        #     self.headers = {
        #         "token": f"{api_key}",
        #         "Content-Type": "application/json",
        #         "Accept": "application/json",
        #     }
        else:
            raise ValueError(
                "Потрібно вказати або api_key, або OAuth credentials (client_id, client_secret, username, password)"
            )

    def _authenticate_oauth(self) -> None:
        """
        Отримання OAuth токену через grant_type=password.

        Raises:
            Exception: Якщо не вдалося отримати токен
        """
        url = f"{self.base_url}/oauth/token"

        data = {
            "grant_type": "password",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "username": self.username,
            "password": self.password,
        }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
        }

        try:
            logger.info("Authenticating with OAuth...")
            response = requests.post(url, data=data, headers=headers, timeout=30)

            if response.ok:
                token_data = response.json()
                self.__oauth_token = token_data.get("access_token")
                if not self.__oauth_token:
                    raise Exception("Access token not found in response")
                logger.info("OAuth authentication successful")
            else:
                error_msg = f"OAuth authentication failed: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise Exception(error_msg)

        except requests.exceptions.Timeout:
            error_msg = "Timeout при OAuth автентифікації"
            logger.error(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            logger.error(f"Error during OAuth authentication: {e}")
            raise

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        retry_on_401: bool = True,
    ) -> Dict[str, Any]:
        """
        Виконання HTTP запиту до Hurma API.

        Args:
            method: HTTP метод (GET, POST, PUT, DELETE)
            endpoint: Шлях до API endpoint
            params: URL параметри запиту
            data: Дані тіла запиту
            retry_on_401: Чи повторювати запит при помилці 401 (Unauthorized)

        Returns:
            JSON дані відповіді

        Raises:
            Exception: Якщо API запит не вдався
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                params=params,
                json=data,
                timeout=30,  # 30 секунд таймаут
            )

            if response.ok:
                return response.json()
            elif response.status_code == 401 and retry_on_401 and self.__oauth_token:
                # OAuth токен закінчився, повторно авторизуємось
                logger.warning(
                    "Отримано 401 Unauthorized. OAuth токен закінчився, повторна авторизація..."
                )
                self._authenticate_oauth()

                # Оновлюємо заголовок з новим токеном
                self.headers["Authorization"] = f"Bearer {self.__oauth_token}"

                # Повторюємо запит (без retry щоб уникнути нескінченного циклу)
                logger.info("Повторюємо запит з новим токеном...")
                return self._make_request(
                    method, endpoint, params, data, retry_on_401=False
                )
            else:
                error_msg = f"Hurma API error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise Exception(error_msg)

        except requests.exceptions.Timeout:
            error_msg = f"Timeout при запиті до Hurma API: {url}"
            logger.error(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            logger.error(f"Error making request to Hurma API: {e}")
            raise

    # ==================== CANDIDATES ====================

    def get_candidates(
        self,
        responsible_recruiter_id: Optional[int] = None,
        vacancy_id: Optional[int] = None,
        stage_id: Optional[int] = None,
        source: Optional[int] = None,
        vacancy_source: Optional[int] = None,
        filter_job_openings: List[int] = None,
        page: int = 1,
        per_page: int = 10,
    ) -> Dict[str, Any]:
        """
        Отримання списку кандидатів.

        Args:
            status: Фільтр за статусом
            vacancy_id: Фільтр за ID вакансії
            page: Номер сторінки для пагінації
            per_page: Кількість елементів на сторінці

        Returns:
            Словник з даними кандидатів
        """
        params = {"page": page, "per_page": per_page}
        if responsible_recruiter_id:
            params["responsible_recruiter_id"] = responsible_recruiter_id
        if stage_id:
            params["stage_id"] = stage_id
        if source:
            params["source"] = source
        if vacancy_source:
            params["vacancy_source"] = vacancy_source
        if vacancy_id:
            params["vacancy_id"] = vacancy_id
        if filter_job_openings:
            params["filter[job_openings]"] = ",".join(
                map(str, filter_job_openings)
            )

        logger.info(f"Getting candidates list with params: {params}")
        return self._make_request("GET", "/candidates", params=params)
    def get_candidate_by_id(self, candidate_id: str) -> Dict[str, Any]:
        """
        Отримання даних конкретного кандидата за ID.

        Args:
            candidate_id: ID кандидата

        Returns:
            Словник з даними кандидата
        """
        logger.info(f"Getting candidate by ID: {candidate_id}")
        return self._make_request(
            "GET",
            f"/candidates/{candidate_id}",
        )
    def stage(
        self, parent_stage_id: int = None, page: int = 1, per_page: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Отримання етапів кандидатів.

        Args:
            parant_stage_id: ID батьківського етапу
            page: Номер сторінки для пагінації
            per_page: Кількість елементів на сторінці

        Returns:
            Список етапів кандидатів
        """
        logger.info("Getting stages for candidates")
        params = {"page": page, "per_page": per_page}
        if parent_stage_id:
            params = {
                "parent_stage_id": parent_stage_id,
                "page": page,
                "per_page": per_page,
            }
        return self._make_request(
            "GET",
            "/stage",
            params=params,
        )

    def get_job_openings(
        self, filter_status: List[int] = None, page: int = 1, per_page: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Отримання вакансій.

        Args:
            page: Номер сторінки для пагінації
            per_page: Кількість елементів на сторінці

        Returns:
            Список вакансій
        """
        logger.info("Getting job openings")
        params = {"page": page, "per_page": per_page}
        if filter_status:
            params["filter[status]"] = filter_status
        return self._make_request(
            "GET",
            "/job-openings",
            params=params,
        )

    def get_job_stages(self, vacancy_id: int, stage: int = None) -> Dict[str, Any]:
        """
        Отримання етапів для конкретної вакансії.

        Args:
            vacancy_id: ID вакансії
        Returns:
            Словник з етапами вакансії
        """
        logger.info(f"Getting job stages for vacancy ID: {vacancy_id}")
        params = {"stage_id": stage} if stage else {}
        return self._make_request(
            "GET",
            f"/job-openings/{vacancy_id}/stages",
            params=params,
        )
