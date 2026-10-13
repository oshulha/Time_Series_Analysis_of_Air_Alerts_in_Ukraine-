"""
conftest.py — додає dataset_pipeline/ до sys.path,
щоб `from pipeline.xxx import yyy` працювало при запуску pytest
з кореня репозиторію або з dataset_pipeline/.
"""
import sys
import os

# dataset_pipeline/ — базова папка для всіх внутрішніх імпортів
sys.path.insert(0, os.path.dirname(__file__))

