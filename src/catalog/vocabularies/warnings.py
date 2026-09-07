class TagsExcluded(UserWarning):
    def __init__(self, excluded_tags: dict[str, list[str]]) -> None:
        self.excluded_tags = excluded_tags
        details = ", ".join(
            f"{field}={values}" for field, values in excluded_tags.items()
        )
        super().__init__(f"Excluded incompatible catalog tags: {details}")
