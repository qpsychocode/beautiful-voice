"""A list-of-dicts model for QML that updates rows in place."""

from __future__ import annotations

from PySide6.QtCore import QAbstractListModel, QByteArray, QModelIndex, Qt, Signal, Property


class DictListModel(QAbstractListModel):
    countChanged = Signal()

    def __init__(self, keys: list[str], id_key: str = "id", parent=None) -> None:
        super().__init__(parent)
        self._keys = keys
        self._id_key = id_key
        self._items: list[dict] = []
        self._roles = {Qt.UserRole + 1 + i: QByteArray(k.encode()) for i, k in enumerate(keys)}
        self._role_of = {k: Qt.UserRole + 1 + i for i, k in enumerate(keys)}

    def roleNames(self):  # noqa: N802
        return self._roles

    def rowCount(self, parent=QModelIndex()):  # noqa: N802
        return 0 if parent.isValid() else len(self._items)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self._items):
            return None
        key = self._roles.get(role)
        if key is None:
            return None
        return self._items[index.row()].get(bytes(key).decode())

    def _count(self) -> int:
        return len(self._items)

    count = Property(int, _count, notify=countChanged)

    def items(self) -> list[dict]:
        return list(self._items)

    def set_items(self, items: list[dict]) -> None:
        self.beginResetModel()
        self._items = [dict(i) for i in items]
        self.endResetModel()
        self.countChanged.emit()

    def row_of(self, item_id) -> int:
        for row, item in enumerate(self._items):
            if item.get(self._id_key) == item_id:
                return row
        return -1

    def get(self, item_id) -> dict | None:
        row = self.row_of(item_id)
        return dict(self._items[row]) if row >= 0 else None

    def update(self, item_id, **changes) -> None:
        row = self.row_of(item_id)
        if row < 0:
            return
        item = self._items[row]
        changed = [k for k, v in changes.items() if item.get(k) != v]
        if not changed:
            return
        item.update(changes)
        idx = self.index(row, 0)
        self.dataChanged.emit(idx, idx, [self._role_of[k] for k in changed if k in self._role_of])

    def insert(self, row: int, item: dict) -> None:
        row = max(0, min(row, len(self._items)))
        self.beginInsertRows(QModelIndex(), row, row)
        self._items.insert(row, dict(item))
        self.endInsertRows()
        self.countChanged.emit()

    def remove(self, item_id) -> None:
        row = self.row_of(item_id)
        if row < 0:
            return
        self.beginRemoveRows(QModelIndex(), row, row)
        del self._items[row]
        self.endRemoveRows()
        self.countChanged.emit()
