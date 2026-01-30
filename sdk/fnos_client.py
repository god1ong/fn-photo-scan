from .base_client import BaseClient


class FnOsClient(BaseClient):
    async def login(self, username, password, *, deviceType='Browser', deviceName='Windows-Google Chrome',
                    stay=False):
        data = {
            "user": username,
            "password": password,
            "deviceType": deviceType,
            "deviceName": deviceName,
            "stay": stay,
            "si": self.si
        }
        response = await self.request('user.login', **data)
        return response

    async def user_info(self):
        response = await self.request('user.info')
        return response
