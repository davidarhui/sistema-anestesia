"""Negociación IntelliVue: pendiente de implementar tras validar la trama."""


class AssociationClient:
    def __init__(self, interface: str = "en8"):
        self.interface = interface

    def associate(self, *args, **kwargs):
        raise NotImplementedError(
            "La Association Request todavía no ha sido validada para este monitor."
        )
