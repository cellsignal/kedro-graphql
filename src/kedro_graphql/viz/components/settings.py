import panel as pn
import param


class Settings(param.Parameterized):
    config = param.Dict()
    form_pathname = param.String(default = "/pipelines/forms")
    pipelines_pathname = param.String(default = "/pipelines/cards")
    search_pathname = param.String(default = "/pipelines/search")
    monitor_pathname = param.String(default = "/pipelines/monitor")

