from dataclasses import dataclass
import os


@dataclass
class Config:
    # Put your AIPIPE token here or set it as an environment variable.
    AIPIPE_TOKEN: str = os.getenv("AIPIPE_TOKEN", "eyJhbGciOiJIUzI1NiJ9.eyJlbWFpbCI6IjI0ZjMwMDMwOThAZHMuc3R1ZHkuaWl0bS5hYy5pbiIsImlhdCI6MTc4MjY0MzA0MCwiaXNzIjoiaHR0cHM6Ly9haXBpcGUub3JnIiwiYXVkIjoiYWlwaXBlLWFwaSIsImV4cCI6MTc4MzI0Nzg0MH0.KAkbngybHgqCQv6qHCldfxXHipGt47wiaBlYEC4123o")


config = Config()
