import logging
import sys
import io
from pathlib import Path


def create_logger(name: str) -> logging.Logger:
    """
    Створення логера з налаштуваннями.
    
    Args:
        name: Назва логера
        
    Returns:
        Налаштований логер
    """
    logger = logging.getLogger(name)
    
    if logger.handlers:
        return logger
    
    logger.setLevel(logging.INFO)
    
    # Консольний handler з UTF-8 для Windows
    # Використовуємо TextIOWrapper для коректної роботи з Unicode
    if sys.platform == 'win32':
        # Для Windows використовуємо stderr з UTF-8 encoding
        console_stream = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    else:
        console_stream = sys.stdout
    
    console_handler = logging.StreamHandler(console_stream)
    console_handler.setLevel(logging.INFO)
    
    # Файловий handler
    log_dir = Path(__file__).parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    file_handler = logging.FileHandler(log_dir / "bot.log", encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    
    # Форматер
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger
