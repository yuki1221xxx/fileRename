import copy
import json
import os
from datetime import datetime

CONFIG_FILE = "config.json"
_config_cache = None


def _load_from_disk():
    """Read config from disk once. Caller clones before returning to keep behavior the same."""
    if not os.path.exists(CONFIG_FILE):
        return {}
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _get_config_cache():
    global _config_cache
    if _config_cache is None:
        _config_cache = _load_from_disk()
    return _config_cache


def load_config():
    """
    Load config with a tiny in-memory cache to avoid repeated disk I/O on startup.
    Returns a deep copy so callers can mutate the result just like before.
    """
    return copy.deepcopy(_get_config_cache())


def save_config(config):
    global _config_cache
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)
    _config_cache = copy.deepcopy(config)


def _make_row_template(now: datetime):
    return {
        "source_path": "",
        "dest_path": "",
        "base_name": "",
        "year": str(now.year),
        "month": f"{now.month:02}",
        "use_date": True,
        "use_underscores": True,
        "selected_file_path": "",
    }


def ensure_initial_config(default_rows: int = 5):
    """
    初回起動時に default_rows ぶんの行を作る。
    既にconfig.jsonがある場合は何もしない。
    """
    if os.path.exists(CONFIG_FILE):
        return
    now = datetime.now()
    config = {}
    for i in range(default_rows):
        config[f"row{i}"] = _make_row_template(now)
    save_config(config)


def get_row_indices():
    """
    config.jsonにある rowX の X をソートしたリストで返す。
    """
    config = _get_config_cache()
    indices = []
    for key in config.keys():
        if key.startswith("row"):
            try:
                idx = int(key[3:])
                indices.append(idx)
            except ValueError:
                continue
    return sorted(indices)


def add_row_config(index: int):
    """
    指定した index の行がまだなければ追加する。
    """
    config = _get_config_cache()
    key = f"row{index}"
    if key in config:
        return
    now = datetime.now()
    config[key] = _make_row_template(now)
    save_config(config)


def delete_row_config(index: int):
    """
    指定した index の行があれば削除する。
    """
    config = load_config()
    key = f"row{index}"
    if key in config:
        del config[key]
        save_config(config)


def get_row_config(index: int):
    """
    指定されたrowだけを取得する。なければ空dict。
    """
    config = _get_config_cache()
    key = f"row{index}"
    return config.get(key, {}).copy()


def update_row_fields(index: int, **fields):
    """
    その時点のconfigを読み直して、そのrowだけを更新して保存する。
    他のrowは触らないので上書き事故が起きない。
    """
    config = load_config()
    key = f"row{index}"
    if key not in config:
        # なければ新しくひな形をつくる
        now = datetime.now()
        config[key] = _make_row_template(now)
    config[key].update(fields)
    save_config(config)


def normalize_row_configs():
    """
    rowの番号に欠番がある場合、row0から詰めて保存し直す。
    例: row0,row1,row4 -> row0,row1,row2 にする
    戻り値は新しいインデックスのリスト [0,1,2,...]
    """
    config = load_config()
    row_items = []
    for key, value in config.items():
        if key.startswith("row"):
            try:
                idx = int(key[3:])
                row_items.append((idx, value))
            except ValueError:
                continue
    row_items.sort(key=lambda x: x[0])

    new_config = {}
    for new_idx, (_, value) in enumerate(row_items):
        new_config[f"row{new_idx}"] = value

    # row以外が将来入る可能性に備えて残す
    for key, value in config.items():
        if not key.startswith("row"):
            new_config[key] = value

    save_config(new_config)
    return list(range(len(row_items)))
