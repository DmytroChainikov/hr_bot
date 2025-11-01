import datetime
from typing import Dict, Any, List
from datetime import date

import requests

from core.logger_settings import create_logger

logger = create_logger(__name__)


class BinotelService:
    def __init__(self, key: str, secret: str):
        self.key = key
        self.secret = secret
        self.base_url = "https://api.binotel.com/api/4.0/stats"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
        }

    def get_record_link(self, call_id: str):
        params = {
            "key": self.key,
            "secret": self.secret,
            "generalCallID": call_id
        }
        url = "https://api.binotel.com/api/4.0/stats/call-record.json"
        response = requests.get(url, headers=self.headers, json=params, timeout=30)
        return response.json()["url"] if response.ok else None


    def get_calls(self, days_back: int = 3) -> Dict[str, Any]:
        """
        Get calls from Binotel API for the specified number of days back.
        
        Args:
            days_back: Number of days to look back for calls (default: 3)
            
        Returns:
            Dictionary containing combined incoming and outgoing call details
            
        Raises:
            Exception: If API request fails
        """
        now = datetime.datetime.now()
        date_from = now.replace(hour=0, minute=0, second=0, microsecond=0) - datetime.timedelta(days=days_back)
        date_to = now.replace(hour=23, minute=59, second=59, microsecond=0)

        params = {
            "key": self.key,
            "secret": self.secret,
            "startTime": int(date_from.timestamp()),
            "stopTime": int(date_to.timestamp()),
        }

        try:
            outgoing_calls = self._get_outgoing_calls(params)
            incoming_calls = self._get_incoming_calls(params)
            incoming_calls["callDetails"] = incoming_calls["callDetails"] | outgoing_calls["callDetails"]
            logger.info(f"Successfully retrieved calls from Binotel API for {days_back} days back")
            return incoming_calls
            
        except Exception as e:
            logger.error(f"Error getting calls from Binotel API: {e}")
            raise

    def _get_outgoing_calls(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get outgoing calls from Binotel API."""
        url = f"{self.base_url}/outgoing-calls-for-period.json"
        response = requests.get(url, headers=self.headers, json=params, timeout=30)
        
        if response.ok:
            result = response.json()
            # Якщо callDetails відсутній, повертаємо порожній словник
            if 'callDetails' not in result or result['callDetails'] is None:
                result['callDetails'] = {}
            return result
        else:
            raise Exception(f"Error getting outgoing calls: {response.status_code} - {response.text}")

    def _get_incoming_calls(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get incoming calls from Binotel API."""
        url = f"{self.base_url}/incoming-calls-for-period.json"
        response = requests.get(url, headers=self.headers, json=params, timeout=30)
        
        if response.ok:
            result = response.json()
            # Якщо callDetails відсутній, повертаємо порожній словник
            if 'callDetails' not in result or result['callDetails'] is None:
                result['callDetails'] = {}
            return result
        else:
            raise Exception(f"Error getting incoming calls: {response.status_code} - {response.text}")

    def get_calls_by_internal_number(
        self, 
        internal_number: str, 
        date_from: datetime.datetime, 
        date_to: datetime.datetime
    ) -> Dict[str, Any]:
        """
        Отримання дзвінків по внутрішньому номеру за період.
        
        Args:
            internal_number: Внутрішній номер (наприклад, '901')
            date_from: Початкова дата та час
            date_to: Кінцева дата та час
            
        Returns:
            Словник з деталями дзвінків
            
        Raises:
            Exception: Якщо API запит не вдався
            
        Example:
            >>> from datetime import datetime
            >>> binotel = BinotelService(key='...', secret='...')
            >>> date_from = datetime(2013, 6, 1, 0, 0, 0)
            >>> date_to = datetime(2013, 6, 7, 23, 59, 59)
            >>> result = binotel.get_calls_by_internal_number('901', date_from, date_to)
            >>> if result['status'] == 'success':
            >>>     print(result['callDetails'])
        """
        url = f"{self.base_url}/list-of-calls-by-internal-number-for-period.json"
        
        params = {
            "key": self.key,
            "secret": self.secret,
            "internalNumber": internal_number,
            "startTime": int(date_from.timestamp()),
            "stopTime": int(date_to.timestamp())
        }
        print(params)
        try:
            response = requests.get(url, headers=self.headers, json=params, timeout=30)
            
            if response.ok:
                result = response.json()
                if result.get('status') == 'success':
                    logger.info(
                        f"Успішно отримано дзвінки для внутрішнього номера {internal_number}: "
                        f"{len(result.get('callDetails', {}))} дзвінків"
                    )
                    return result
                else:
                    error_msg = f"API помилка {result.get('code')}: {result.get('message')}"
                    logger.error(error_msg)
                    raise Exception(error_msg)
            else:
                raise Exception(
                    f"Помилка отримання дзвінків по внутрішньому номеру: "
                    f"{response.status_code} - {response.text}"
                )
        
        except requests.exceptions.Timeout:
            error_msg = f"Timeout при запиті дзвінків для номера {internal_number}"
            logger.error(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            logger.error(f"Помилка отримання дзвінків по внутрішньому номеру {internal_number}: {e}")
            raise

    def get_calls_for_external_number(self, external_numbers: List[str]) -> Dict[str, Any]:
        """
        Get call history for specific external numbers from Binotel API.
        
        Args:
            external_numbers: List of external phone numbers to get history for
            
        Returns:
            Dictionary containing call history for the specified external numbers
            
        Raises:
            Exception: If API request fails
        """
        url = f"{self.base_url}/history-by-external-number.json"
        
        body = {
            "key": self.key,
            "secret": self.secret,
            "externalNumbers": external_numbers
        }
        
        try:
            response = requests.post(url, headers=self.headers, json=body)
            
            if response.ok:
                logger.info(f"Successfully retrieved call history for {len(external_numbers)} external numbers")
                return response.json()
            else:
                raise Exception(f"Error getting call history for external numbers: {response.status_code} - {response.text}")
                
        except Exception as e:
            logger.error(f"Error getting call history for external numbers from Binotel API: {e}")
            raise

    def download_call(self, call_id):
        """Download call recording to files/calls/ directory"""
        import os
        link = self.get_record_link(call_id)
        
        # Create directory if it doesn't exist
        calls_dir = "files/calls"
        os.makedirs(calls_dir, exist_ok=True)
        
        path = f"{calls_dir}/{call_id}.mp3"
        response = requests.get(link, stream=True)
        response.raise_for_status()

        with open(path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        return path

    def get_calls_from_to(self, date_from, date_to):
        params = {
            "key": self.key,
            "secret": self.secret,
            "startTime": int(date_from.timestamp()),
            "stopTime": int(date_to.timestamp()),
        }

        try:
            outgoing_calls = self._get_outgoing_calls(params)
            incoming_calls = self._get_incoming_calls(params)
            
            # Перевіряємо наявність callDetails у обох відповідях
            out_details = outgoing_calls.get("callDetails") or {}
            in_details = incoming_calls.get("callDetails") or {}
            
            # Об'єднуємо дзвінки
            if isinstance(out_details, dict) and isinstance(in_details, dict):
                incoming_calls["callDetails"] = in_details | out_details
            else:
                incoming_calls["callDetails"] = {}
                
            return incoming_calls

        except Exception as e:
            logger.error(f"Error getting calls from Binotel API: {e}")
            raise
    
    def get_calls_for_date(self, target_date: datetime.date) -> List[Dict[str, Any]]:
        """
        Отримати всі дзвінки за конкретну дату
        
        Args:
            target_date: Дата для отримання дзвінків
            
        Returns:
            Список дзвінків
        """
        # Початок та кінець дня
        date_from = datetime.datetime.combine(target_date, datetime.time(0, 0, 0))
        date_to = datetime.datetime.combine(target_date, datetime.time(23, 59, 59))
        
        try:
            result = self.get_calls_from_to(date_from, date_to)
            
            # Повертаємо список деталей дзвінків
            call_details = result.get('callDetails', {})
            calls_list = []
            
            # callDetails це словник де ключі - це ID дзвінків
            for call_id, call_data in call_details.items():
                call_data['callId'] = call_id  # Додаємо ID до даних
                calls_list.append(call_data)
            
            logger.info(f"Отримано {len(calls_list)} дзвінків за {target_date}")
            return calls_list
            
        except Exception as e:
            logger.error(f"Помилка отримання дзвінків за {target_date}: {e}")
            return []
