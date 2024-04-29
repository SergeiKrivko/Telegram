from pywtdlib.client import Client
from typing import Callable, Optional, Any, Type

from lib import tg


class TgClient(Client):

    def __init__(
            self,
            api_id: int,
            api_hash: str,
            use_file_database: Optional[bool] = False,
            use_chat_info_database: Optional[bool] = False,
            use_message_database: Optional[bool] = False,
            use_secret_chats: Optional[bool] = False,
            use_test_dc: Optional[bool] = False,
            enable_storage_optimizer: Optional[bool] = True,
            wait_timeout: Optional[int] = 1,
            verbosity: Optional[int] = 1,
    ) -> None:
        super().__init__(api_id, api_hash, use_file_database, use_chat_info_database, use_message_database,
                         use_secret_chats, use_test_dc, enable_storage_optimizer, wait_timeout, verbosity)
        self.console_authentication = True
        self._authorization_state = None
        self._authorization_handler = None

        self._subscribers_all = []
        self._routers: dict[Type: dict[tuple: Router]] = dict()
        self._subscribers: dict[Type: list[Subscriber]] = dict()

        self.chats_is_loaded = False

        tg.client = self

    def send(self, data: dict):
        # print(data)
        self.tdjson.send(data)

    def func(self, dct):
        return self.tdjson.execute(dct)

    def set_authorization_handler(self, authorization_handler: Callable) -> None:
        self._authorization_handler = authorization_handler

    def authenticate_user(self, event_dict: dict):
        if self.console_authentication:
            super().authenticate_user(event_dict)
            return
        try:
            event = tg.get_object(event_dict)
        except Exception:
            return
        if isinstance(event, tg.UpdateAuthorizationState):
            self._authorization_state = event.authorization_state
            if isinstance(self._authorization_state, tg.AuthorizationStateWaitTdlibParameters):
                self.send_tdlib_parameters()
            elif isinstance(self._authorization_state, tg.AuthorizationStateReady):
                self.get_all_chats()
                self.authorized = True
                # tg.getRecommendedChatFilters()
                self.logger.info("User authorized")
            elif self._authorization_state is not None:
                self._authorization_handler(self._authorization_state)

    def send_authentication(self, str1: str, str2: str):
        if isinstance(self._authorization_state, tg.AuthorizationStateWaitPhoneNumber):
            self.send({"@type": "setAuthenticationPhoneNumber", "phone_number": str1})
        elif isinstance(self._authorization_state, tg.AuthorizationStateWaitCode):
            self.send({"@type": "checkAuthenticationCode", "code": str1})
        elif isinstance(self._authorization_state, tg.AuthorizationStateWaitRegistration):
            self.send({"@type": "registerUser", "first_name": str1, "last_name": str2})
        elif isinstance(self._authorization_state, tg.AuthorizationStateWaitEmailAddress):
            self.send({"@type": "setAuthenticationEmailAddress", "email_address": str1})
        elif isinstance(self._authorization_state, tg.AuthorizationStateWaitEmailCode):
            self.send({"@type": "checkAuthenticationEmailCode",
                       "code": {"@type": "emailAddressAuthenticationCode", "code": str1}})
        elif isinstance(self._authorization_state, tg.AuthorizationStateWaitPassword):
            self.send({"@type": "checkAuthenticationPassword", "password": str1})

    def subscribe(self, event: Type, func: Callable, **kwargs) -> 'Subscriber':
        if kwargs:
            key = tuple(sorted(kwargs.keys()))
            if event not in self._routers:
                self._routers[event] = dict()
            if key not in self._routers[event]:
                router = Router(event, key)
                self._routers[event][key] = router
            else:
                router = self._routers[event][key]
            return router.subscribe(func, kwargs)
        else:
            if event not in self._subscribers:
                self._subscribers[event] = []
            subscriber = Subscriber(func, self._subscribers[event])
            self._subscribers[event].append(subscriber)
            return subscriber

    def subscribe_all(self, func: Callable) -> 'Subscriber':
        subscriber = Subscriber(func, self._subscribers_all)
        self._subscribers_all.append(subscriber)
        return subscriber

    def execute(self):
        # start the client by sending request to it
        self.get_authorization_state()

        # main events cycle
        while True:
            event_dict = self.tdjson.receive()
            if event_dict:
                if not self.authorized:
                    self.authenticate_user(event_dict)

                event = tg.get_object(event_dict)
                if event.__class__ in self._subscribers:
                    for el in self._subscribers[event.__class__]:
                        el(event)
                for el in self._subscribers_all:
                    el(event)


class Subscriber:
    def __init__(self, func: Callable, lst: list):
        self.func = func
        self.__lst = lst

    def __call__(self, event):
        return self.func(event)

    def unsubscribe(self):
        self.__lst.remove(self)


class Router:
    def __init__(self, event_class: Type, keys: tuple[str, ...]):
        self.__event = event_class
        self.__keys = keys

        self.__subscribers: dict[tuple: list[Subscriber]] = dict()

    def subscribe(self, func: Callable, keys: dict[str: Any]):
        key = [keys[k] for k in self.__keys]
        if key not in self.__subscribers:
            self.__subscribers[key] = lst = []
        else:
            lst = self.__subscribers[key]
        subscriber = Subscriber(func, lst)
        lst.append(subscriber)
        return subscriber

    def __call__(self, event):
        key = (getattr(event, key) for key in self.__keys)
        for el in self.__subscribers.get(key, []):
            el(event)
