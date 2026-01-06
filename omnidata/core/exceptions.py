"""
自定义异常模块
"""


class OmniDataError(Exception):
    """OmniData 基础异常"""

    pass


class BrowserPoolError(OmniDataError):
    """浏览器池异常"""

    pass


class BrowserAcquisitionError(BrowserPoolError):
    """获取浏览器失败异常"""

    pass


class BrowserTimeoutError(BrowserPoolError):
    """浏览器操作超时异常"""

    pass


class SpiderError(OmniDataError):
    """爬虫异常"""

    pass


class SpiderValidationError(SpiderError):
    """参数验证失败异常"""

    pass


class SpiderNotFoundError(SpiderError):
    """爬虫未找到异常"""

    pass


class SpiderRegistrationError(SpiderError):
    """爬虫注册异常"""

    pass


class LoginError(OmniDataError):
    """登录异常基类"""

    pass


class LoginValidationError(LoginError):
    """登录参数验证失败异常"""

    pass


class LoginTimeoutError(LoginError):
    """登录超时异常"""

    pass


class LoginNotFoundError(LoginError):
    """登录类未找到异常"""

    pass


class LoginRegistrationError(LoginError):
    """登录类注册异常"""

    pass
