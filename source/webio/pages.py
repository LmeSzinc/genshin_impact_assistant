from source.util import *
from pywebio import *
from webio.util import *

import hashlib
import json
import os
import socket
import threading
import time

from source import listening, webio
from source.webio import manager
from source.webio.page_manager import Page
import flow_state
import collector_lib


# from source.webio.log_handler import webio_poster


class MainPage(Page):
    def __init__(self):
        super().__init__()
        self.log_list = []
        self.log_list_lock = threading.Lock()
        self.ui_statement = -1

    # todo:多语言支持

    def _on_load(self):  # 加载事件
        super()._on_load()
        self._load()  # 加载主页
        t = threading.Thread(target=self._event_thread, daemon=False)  # 创建事件线程
        session.register_thread(t)  # 注册线程
        t.start()  # 启动线程
        pin.pin['FlowMode'] = listening.current_flow

    def _event_thread(self):
        while self.loaded:  # 当界面被加载时循环运行
            try:
                pin.pin['isSessionExist']
            except SessionNotFoundException:
                logger.info(_("未找到会话，可能由于窗口关闭。请刷新页面重试。"))
                return
            if pin.pin['FlowMode'] != listening.current_flow:  # 比较变更是否被应用
                listening.current_flow = pin.pin['FlowMode']  # 应用变更
                self.log_list_lock.acquire()
                output.put_text(_("正在导入模块, 可能需要一些时间。"), scope='LogArea').style(
                    f'color: black; font_size: 20px')
                output.put_text(_("在导入完成前，请不要切换页面。"), scope='LogArea').style(
                    f'color: black; font_size: 20px')
                self.log_list_lock.release()
                listening.call_you_import_module()
            self.log_list_lock.acquire()
            for text, color in self.log_list:
                if text == "$$end$$":
                    output.put_text("", scope='LogArea')
                else:
                    output.put_text(text, scope='LogArea', inline=True).style(f'color: {color}; font_size: 20px')
            self.log_list.clear()
            self.log_list_lock.release()

            if flow_state.current_statement != self.ui_statement:
                self.ui_statement = flow_state.current_statement
                output.clear(scope="StateArea")
                f = False
                for i in self.ui_statement:
                    t = self.ui_statement[i]
                    if t == 0:
                        continue
                    else:
                        output.put_text(flow_state.get_statement_code_name(self.ui_statement[i]), scope="StateArea")
                        f = True
                if not f:
                    output.put_text(flow_state.get_statement_code_name(0), scope="StateArea")

            time.sleep(0.1)

    
        
    
    def _load(self):
        # 标题
        output.put_markdown('# Main', scope=self.main_scope)

        output.put_row([
            # 页面切换按钮
            
            output.put_buttons(self._value_list2buttons_type(list(manager.page_dict)), onclick=webio.manager.load_page, scope=self.main_scope),
            # 获得链接按钮
            output.put_button(label=_("Get IP address"), onclick=self.on_click_ip_address, scope=self.main_scope)

        ], scope=self.main_scope)

        output.put_row([  # 横列
            output.put_column([  # 左竖列
                output.put_markdown(_('## Options')),  # 左竖列标题

                output.put_row([  # FlowMode
                    output.put_text(_('FlowMode')),
                    pin.put_select(('FlowMode'), [
                        {'label': _('Idle'), 'value': listening.FLOW_IDLE},
                        {'label': _('AutoCombat'), 'value': listening.FLOW_COMBAT},
                        {'label': _('AutoDomain'), 'value': listening.FLOW_DOMAIN},
                        {'label': _('AutoCollector'), 'value': listening.FLOW_COLLECTOR}
                    ])]),
                # Button_StartStop
                output.put_row([output.put_text(_('启动/停止')), output.put_scope('Button_StartStop')]),

                output.put_markdown(_('## Statement')),

                output.put_row([output.put_text(_('当前状态')), output.put_scope('StateArea')])

            ]), None,
            output.put_scope('Log')

        ], scope=self.main_scope, size='30% 10px 70%')

        # PickUpButton
        output.put_button(label=str(listening.FEAT_PICKUP), onclick=self.on_click_pickup, scope='Button_PickUp')
        # Button_StartStop
        output.put_button(label=str(listening.startstop_flag), onclick=self.on_click_startstop,
                          scope='Button_StartStop')

        # Log
        output.put_markdown(_('## Log'), scope='Log')
        output.put_scrollable(output.put_scope('LogArea'), height=600, keep_bottom=True, scope='Log')
        '''self.main_pin_change_thread = threading.Thread(target=self._main_pin_change_thread, daemon=False)
        self.main_pin_change_thread.start()'''

    def on_click_pickup(self):
        output.clear('Button_PickUp')
        listening.FEAT_PICKUP = not listening.FEAT_PICKUP
        output.put_button(label=str(listening.FEAT_PICKUP), onclick=self.on_click_pickup, scope='Button_PickUp')

    def on_click_startstop(self):
        output.clear('Button_StartStop')
        listening.startstop()
        output.put_button(label=str(listening.startstop_flag), onclick=self.on_click_startstop,
                          scope='Button_StartStop')

    def on_click_ip_address(self):
        LAN_ip = f"{socket.gethostbyname(socket.gethostname())}{session.info.server_host[session.info.server_host.index(':'):]}"
        WAN_ip = _("Not Enabled")
        output_text = _('LAN IP') + " : " + LAN_ip + '\n' + _("WAN IP") + ' : ' + WAN_ip
        output.popup(f'ip address', output_text, size=output.PopupSize.SMALL)

    def logout(self, text: str, color='black'):
        if self.loaded:
            self.log_list_lock.acquire()
            self.log_list.append((text, color))
            self.log_list_lock.release()

    def _on_unload(self):
        pass


class ConfigPage(Page):
    def __init__(self):
        super().__init__()

        # self.main_scope = "SettingPage"

        self.exit_popup = None
        self.last_file = None
        self.file_name = ''

        self.config_files = []
        self.config_files_name = []
        self._load_config_files()
        self.can_check_select = True
        self.can_remove_last_scope = False
        # 注释显示模式在这改
        self.mode = True
        self.read_only = False

    def _load_config_files(self):
        for root, dirs, files in os.walk('config'):
            for f in files:
                if f[f.index('.') + 1:] == "json":
                    self.config_files.append({"label": f, "value": os.path.join(root, f)})

    def _load(self):
        self.last_file = None

        # 标题
        output.put_markdown(_('# Config'), scope=self.main_scope)

        # 页面切换按钮
        output.put_buttons(self._value_list2buttons_type(list(manager.page_dict)), onclick=webio.manager.load_page, scope=self.main_scope)

        # 配置页
        output.put_markdown(_('## config:'), scope=self.main_scope)

        output.put_scope("select_scope", scope=self.main_scope)
        pin.put_select('file', self._config_file2lableAfile(self.config_files), scope="select_scope")

    def _on_load(self):
        super()._on_load()
        self._load()  # 加载页面
        t = threading.Thread(target=self._event_thread, daemon=False)
        session.register_thread(t)  # 注册线程
        t.start()

    def _config_file2lableAfile(self, l1):
        replace_dict = {
            "auto_aim.json": _("auto_aim.json"),
            "auto_collector.json": _("auto_collector.json"),
            "auto_combat.json": _("auto_combat.json"),
            "auto_domain.json": _("auto_domain.json"),
            "auto_pickup.json": _("auto_pickup.json"),
            "auto_pickup_default_blacklist.json": _("auto_pickup_default_blacklist.json"),
            "config.json": _("config.json"),
            "keymap.json": _("keymap.json"),
            "character.json": _("character.json"),
            "character_dist.json": _("character_dist.json"),
            "team.json": _("team.json"),
            "team_example_2.json": _("team_example_2.json"),
            "collected.json": _("collected.json"),
            "collection_blacklist.json": _("collection_blacklist.json"),
            "collection_log.json": _("collection_log.json"),
            "auto_collector.json": _("auto_collector.json")
        }
        
        for i in range(len(l1)):
            l1[i]["label"] = replace_dict.setdefault(l1[i]["label"], l1[i]["label"])
        return l1
    
    # 重新加载选项
    def _reload_select(self):
        self.can_check_select = False
        self._load_config_files()
        output.clear("select_scope")
        pin.put_select('file', self._config_file2lableAfile(self.config_files), scope="select_scope")
        self.can_check_select = True
    
    # 循环线程
    def _event_thread(self):
        while self.loaded:
            if not self.can_check_select:
                time.sleep(1)
                continue
            try:
                pin.pin['isSessionExist']
            except SessionNotFoundException:
                logger.info(_("未找到会话，可能由于窗口关闭。请刷新页面重试。"))
                return
                
            if pin.pin['file'] != self.last_file:  # 当下拉框被更改时
                self.last_file = pin.pin['file']

                if self.can_remove_last_scope:  # 判断是否可以移除
                    output.remove('now')
                else:
                    self.can_remove_last_scope = True

                output.put_scope('now', scope=self.main_scope)  # 创建配置页scope
                
                
                self.put_setting(pin.pin['file'])  # 配置配置页

            time.sleep(1)

    def _before_load_json(self):
        pass
     
    def put_setting(self, name=''):
        self.file_name = name
        self._before_load_json()
        output.put_markdown('## {}'.format(name), scope='now')  # 标题
        with open(name, 'r', encoding='utf8') as f:
            j = json.load(f)

        # with open(os.path.join(root_path, "config", "settings", "config.json"), 'r', encoding='utf8') as f:
        #     lang = json.load(f)["lang"]
        doc_name = f'{name}.{global_lang}.jsondoc'

        if os.path.exists(doc_name):
            with open(doc_name, 'r', encoding='utf8') as f:
                doc = json.load(f)
        elif os.path.exists(f'{name}.en_US.jsondoc'):
            with open(f'{name}.en_US.jsondoc', 'r', encoding='utf8') as f:
                doc = json.load(f)
        else:
            doc = {}
        self.put_json(j, doc, 'now', level=3)  # 载入json
        
        if not self.read_only:
            output.put_button('save', scope='now', onclick=self.save)

    # 保存json文件
    def save(self):

        j = json.load(open(self.file_name, 'r', encoding='utf8'))

        json.dump(self.get_json(j), open(self.file_name, 'w', encoding='utf8'), ensure_ascii=False, indent=4)
        # output.put_text('saved!', scope='now')
        output.toast(_('saved!'))

    # 
    def get_json(self, j: dict, add_name=''):
        rt_json = {}
        for k in j:
            k_sha1 = hashlib.sha1(k.encode('utf8')).hexdigest()
            v = j[k]
            if type(v) == dict:
                rt_json[k] = self.get_json(v, add_name='{}-{}'.format(add_name, k_sha1))

            elif type(v) == list:

                # 判断是否为dict列表
                is_dict_list = True
                for i in v:
                    is_dict_list = is_dict_list and (type(i) == dict)

                if is_dict_list:
                    # 这个是dict的id,是在列表的位置,从1开始,当然也可以改成从0开始,都一样
                    dict_id = 0
                    # 在当前dict列表里循环,取出每一个dict
                    rt_list = []
                    for i in v:
                        # 计次+1
                        dict_id += 1
                        rt_list.append(
                            self.get_json(v[dict_id - 1], add_name='{}-{}-{}'.format(add_name, k_sha1, str(dict_id))))
                    rt_json[k] = rt_list
                else:
                    rt_json[k] = list_text2list(pin.pin['{}-{}'.format(add_name, k_sha1)])
            else:
                rt_json[k] = pin.pin['{}-{}'.format(add_name, k_sha1)]

        return rt_json

    def _on_unload(self):
        if not self.read_only:
            j = json.load(open(self.file_name, 'r', encoding='utf8'))
            self.exit_popup = True
            if not is_json_equal(json.dumps(self.get_json(j)), json.dumps(j)):
                self.exit_popup = False
                output.popup(_('Do you need to save changes?'), [
                    output.put_buttons([(_('No'), 'No'), (_('Yes'), 'Yes')], onclick=self.popup_button)
                ])
            while not self.exit_popup:
                time.sleep(0.1)

    def popup_button(self, val):
        if val == 'No':
            self.close_popup()
        elif val == 'Yes':
            self.save_and_exit_popup()

    def save_and_exit_popup(self):
        self.save()
        output.close_popup()
        self.exit_popup = True

    def close_popup(self):
        output.close_popup()
        self.exit_popup = True
    
    # 展示str型项
    def _show_str(self, doc_items, component_name, display_name, scope_name, v):
        if doc_items:
            pin.put_select(component_name,
                            [{"label": i, "value": i} for i in doc_items], value=v,
                            label=display_name,
                            scope=scope_name)
        else:
            pin.put_input(component_name, label=display_name, value=v, scope=scope_name)
    
    # 展示inf型项
    def _show_int(self, doc_items, component_name, display_name, scope_name, v):
        if doc_items:
            pin.put_select(component_name,
                            [{"label": i, "value": i} for i in doc_items], value=v,
                            label=display_name,
                            scope=scope_name)
        else:
            pin.put_input(component_name, label=display_name, value=v, scope=scope_name, type='number')
    
    # 展示float型项
    def _show_float(self, doc_items, component_name, display_name, scope_name, v):
        if doc_items:
            pin.put_select(component_name,
                            [{"label": i, "value": i} for i in doc_items], value=v,
                            label=display_name,
                            scope=scope_name)
        else:
            pin.put_input(component_name, label=display_name, value=v, scope=scope_name, type='float')
    
    # 展示bool型项
    def _show_bool(self, component_name, display_name, scope_name, v):
        pin.put_select(component_name,
            [{"label": 'True', "value": True}, {"label": 'False', "value": False}], value=v,
            label=display_name,
            scope=scope_name)
    
    # 展示dict型项
    def _show_dict(self, level, component_name, display_name, scope_name, doc, v):
        output.put_scope(component_name, scope=scope_name)
        output.put_markdown('#' * level + ' ' + display_name, scope=component_name)
        self.put_json(v, doc, component_name, add_name=component_name,
                        level=level + 1)
    
    # 展示list/list&dict型项
    def _show_list(self, level, display_name, scope_name, component_name, doc, v):
        # 判断是否为dict列表
        is_dict_list = True
        for i in v:
            is_dict_list = is_dict_list and (type(i) == dict)

        if is_dict_list:
            output.put_markdown('#' * level + ' ' + display_name,
                                scope=scope_name)
            # 差点把我绕晕....
            # 这个是dict的id,是在列表的位置,从1开始,当然也可以改成从0开始,都一样
            dict_id = 0
            # 在当前dict列表里循环,取出每一个dict
            for i in v:
                # 计次+1
                dict_id += 1

                # 创建一个容器以容纳接下来的dict,第一个是控件名称,为了防止重复,加上了dict id,后面那个是当前容器id
                output.put_scope(component_name + '-' + str(dict_id), scope=scope_name)
                # 写标题,第一项是标题文本,遵守markdown语法,第二项是当前容器名称
                output.put_markdown('#' * (level + 1) + ' ' + str(dict_id),
                                    scope=component_name + '-' + str(dict_id))
                # 写dict,第一项为输入的dict,第二项为doc,第三项为当前容器名称,第四项为控件名称前缀,最后是缩进等级
                self.put_json(i, doc, component_name + '-' + str(dict_id),
                                component_name + '-' + str(dict_id),
                                level=level + 2)
        else:
            pin.put_textarea(component_name, label=display_name, value=list2format_list_text(v),
                                scope=scope_name)
    
    # 显示json
    def put_json(self, j: dict, doc: dict, scope_name, add_name='', level=1):
        for k in j:
            v = j[k]
            # 获取注释
            doc_now = ''
            doc_now_data = {}
            doc_items = None
            if k in doc:
                # 判断doc的类型
                if type(doc[k]) == dict:
                    if 'doc' in doc[k]:
                        doc_now = doc[k]['doc']
                    if 'data' in doc[k]:
                        doc_now_data = doc[k]['data']
                    if 'select_items' in doc[k]:
                        doc_items = doc[k]['select_items']
                if type(doc[k]) == str:
                    doc_now = doc[k]
            # 取显示名称
            display_name = doc_now if doc_now else k if self.mode else '{} {}'.format(k, doc_now)

            k_sha1 = hashlib.sha1(k.encode('utf8')).hexdigest()
            component_name = '{}-{}'.format(add_name, k_sha1)
            if type(v) == str or v is None:
                self._show_str(doc_items, component_name, display_name, scope_name, v)
            elif type(v) == int:
                self._show_int(doc_items, component_name, display_name, scope_name, v)
            elif type(v) == float:
                self._show_float(doc_items, component_name, display_name, scope_name, v)
            elif type(v) == bool:
                self._show_bool(component_name, display_name, scope_name, v)
            elif type(v) == dict:
                self._show_dict(level, component_name, display_name, scope_name, doc, v)
            elif type(v) == list:
                self._show_list(level, display_name, scope_name, component_name, doc, v)


class SettingPage(ConfigPage):
    def __init__(self):
        super().__init__()

    def _load(self):
        self.last_file = None

        # 标题
        output.put_markdown(_('# Setting'), scope=self.main_scope)

        # 页面切换按钮
        output.put_buttons(self._value_list2buttons_type(list(manager.page_dict)), onclick=webio.manager.load_page, scope=self.main_scope)

        # 配置页
        output.put_markdown(_('## config:'), scope=self.main_scope)
        output.put_scope("select_scope", scope=self.main_scope)

        pin.put_select('file', self._config_file2lableAfile(self.config_files), scope="select_scope")

    def _load_config_files(self):
        for root, dirs, files in os.walk('config\\settings'):
            for f in files:
                if f[f.index('.') + 1:] == "json":
                    self.config_files.append({"label": f, "value": os.path.join(root, f)})


class CombatSettingPage(ConfigPage):
    def __init__(self):
        super().__init__()

    def _load_config_files(self):
        self.config_files = []
        for root, dirs, files in os.walk('config\\tactic'):
            for f in files:
                if f[f.index('.') + 1:] == "json":
                    self.config_files.append({"label": f, "value": os.path.join(root, f)})

    def _load(self):
        self.last_file = None

        # 标题
        output.put_markdown(_('# CombatSetting'), scope=self.main_scope)

        # 页面切换按钮
        output.put_buttons(self._value_list2buttons_type(list(manager.page_dict)), onclick=webio.manager.load_page, scope=self.main_scope)

        # 添加team.json
        output.put_markdown(_('# Add team'), scope=self.main_scope)

        # 添加team.json按钮
        output.put_row([
            output.put_button(_("Add team"), onclick=self.onclick_add_teamjson, scope=self.main_scope),
            None,
            output.put_button(_("Add team with characters"), onclick=self.onclick_add_teamjson_withcharacters,
                              scope=self.main_scope)],
            scope=self.main_scope, size="10% 10px 20%")

        # 配置页
        output.put_markdown(_('## config:'), scope=self.main_scope)
        output.put_scope("select_scope", scope=self.main_scope)
        pin.put_select('file', self._config_file2lableAfile(self.config_files), scope="select_scope")

    def onclick_add_teamjson(self):
        n = input.input('team name')
        shutil.copy(os.path.join(root_path, "config\\tactic\\team.uijsontemplate"),
                    os.path.join(root_path, "config\\tactic", n + '.json'))
        self._reload_select()

    def onclick_add_teamjson_withcharacters(self):
        n = input.input('team name')
        shutil.copy(os.path.join(root_path, "config\\tactic\\team_with_characters.uijsontemplate"),
                    os.path.join(root_path, "config\\tactic", n + '.json'))
        self._reload_select()
        pass


class CollectorSettingPage(ConfigPage):
    def __init__(self):
        super().__init__()

    def _load_config_files(self):
        self.config_files = []
        for root, dirs, files in os.walk('config\\auto_collector'):
            for f in files:
                if f[f.index('.') + 1:] == "json":
                    self.config_files.append({"label": f, "value": os.path.join(root, f)})
        self.config_files.append({"label": "auto_collector.json", "value": os.path.join(root_path, "config\\settings\\auto_collector.json")})

    # 重置列表
    @staticmethod
    def _reset_list_textarea(x):
        pin.pin[x] = "[\n\n]"
    
    def _load(self):
        self.last_file = None

        # 标题
        output.put_markdown('# ' + _('CollectorSetting'), scope=self.main_scope)

        # 页面切换按钮
        output.put_buttons(self._value_list2buttons_type(list(manager.page_dict)), onclick=webio.manager.load_page, scope=self.main_scope)

        # 配置页
        output.put_markdown(_('## config:'), scope=self.main_scope)
        output.put_scope("select_scope", scope=self.main_scope)
        pin.put_select('file', self._config_file2lableAfile(self.config_files), scope="select_scope")
    
    def _clean_textarea(self, set_value):
        set_value("")
    
    def _onclick_col_log_operate(self, btn_value:str):
        if btn_value == "$COLLECTED$":
            collector_lib.generate_collected_from_log()
            toast_succ()
        elif btn_value == "$BLACKLIST$":
            collector_lib.generate_masked_col_from_log()
            toast_succ()
    
    def _before_load_json(self):
        if "collection_log.json" in self.file_name:
            self.read_only = True
            output.put_buttons([
                (_("Automatic generate a list of collected items"), "$COLLECTED$"),
                (_("Automatic generate a list of blacklist items"), "$BLACKLIST$")], 
                onclick=self._onclick_col_log_operate,
                scope="now"
            )
        else:
            self.read_only = False
        return super()._before_load_json()
    
    def _on_click_collectionlog(self, btn_value:str):
        # btn value: $AddToBlackList$#KEY#ID
        collect_key = btn_value.split('#')[1]
        collect_id = int(btn_value.split('#')[2])
        if "$AddToBlackList$" in btn_value:
            collector_lib.add_to_blacklist(collect_key, collect_id)
            toast_succ()
        elif "$AddToCollected$" in btn_value:
            collector_lib.add_to_collected(collect_key, collect_id)
            toast_succ()
            
        
    def _show_list(self, level, display_name, scope_name, component_name, doc, v):
        # 判断是否为dict列表
        is_dict_list = True
        for i in v:
            is_dict_list = is_dict_list and (type(i) == dict)

        if is_dict_list:
            
            output.put_markdown('#' * level + ' ' + display_name,
                                scope=scope_name)
            if "collection_log.json" in self.file_name:
                for iii in range(len(v)):
                    v[iii]["picked item"] = str(v[iii]["picked item"])
                v = v[::-1]
                show_list = []
                for iii in range(len(v)):
                    ctime = v[iii]["time"][:v[iii]["time"].index('.')]
                    show_list.append( [v[iii]["error_code"], v[iii]["id"], v[iii]["picked item"], ctime, 
                                 output.put_buttons([
                                     (_("Add to blacklist"), f"$AddToBlackList$#{display_name}#{v[iii]['id']}"),
                                     (_("Add to collected"), f"$AddToCollected$#{display_name}#{v[iii]['id']}")],
                                 onclick=self._on_click_collectionlog, small=True)])
                a1,a2,a3,a4 = collector_lib.col_succ_times_from_log(display_name, day=1)
                b1,b2,b3,b4 = collector_lib.col_succ_times_from_log(display_name, day=7)
                c1,c2,c3,c4 = collector_lib.col_succ_times_from_log(display_name, day=15)
                d1,d2,d3,d4 = collector_lib.col_succ_times_from_log(display_name, day=900)
                output.put_collapse(_("展开/收起"), [
                    
                    output.put_text(f"{_('Within')} 1   {_('day(s)')} {_('success rate')}:{a1} {_('total num')}:{a2} {_('success num')}:{a3} {_('fail num')}:{a4}"),
                    output.put_text(f"{_('Within')} 7   {_('day(s)')} {_('success rate')}:{b1} {_('total num')}:{b2} {_('success num')}:{b3} {_('fail num')}:{b4}"),
                    output.put_text(f"{_('Within')} 15  {_('day(s)')} {_('success rate')}:{c1} {_('total num')}:{c2} {_('success num')}:{c3} {_('fail num')}:{c4}"),
                    output.put_text(f"{_('Within')} 900 {_('day(s)')} {_('success rate')}:{d1} {_('total num')}:{d2} {_('success num')}:{d3} {_('fail num')}:{d4}"),
                    output.put_table(show_list, header=["error_code", "id", "picked item", "time", "buttons"])
                ], scope=scope_name)
                
                
            else:
                # 差点把我绕晕....
                # 这个是dict的id,是在列表的位置,从1开始,当然也可以改成从0开始,都一样
                dict_id = 0
                # 在当前dict列表里循环,取出每一个dict
                for i in v:
                    # 计次+1
                    dict_id += 1
                    
                    
                # 创建一个容器以容纳接下来的dict,第一个是控件名称,为了防止重复,加上了dict id,后面那个是当前容器id
                    output.put_scope(component_name + '-' + str(dict_id), scope=scope_name)
                    # 写标题,第一项是标题文本,遵守markdown语法,第二项是当前容器名称
                    output.put_markdown('#' * (level + 1) + ' ' + str(dict_id),
                                        scope=component_name + '-' + str(dict_id))
                    # 写dict,第一项为输入的dict,第二项为doc,第三项为当前容器名称,第四项为控件名称前缀,最后是缩进等级
                    self.put_json(i, doc, component_name + '-' + str(dict_id),
                                    component_name + '-' + str(dict_id),
                                    level=level + 2)
        else:
            # 清除按钮
            if "collected.json" in self.file_name:
                output.put_row([
                    pin.put_textarea(component_name, label=display_name, value=list2format_list_text(v)),
                    None,
                    output.put_button(_("clean list"), onclick=lambda:self._reset_list_textarea(component_name))
                    ]
                , scope=scope_name,size="85% 5% 10%")
            elif "collection_log.json" in self.file_name:
                # output.put_table()
                output.put_text(f"{display_name} : {list2format_list_text(v, inline=True)}", scope=scope_name)
            else:
                pin.put_textarea(component_name, label=display_name, value=list2format_list_text(v), scope=scope_name)
                
    
    def _show_str(self, doc_items, component_name, display_name, scope_name, v):
        if doc_items:
            pin.put_select(component_name,
                            [{"label": i, "value": i} for i in doc_items], value=v,
                            label=display_name,
                            scope=scope_name)
        else:
            if "collection_log.json" in self.file_name:
                output.put_text(f"{display_name} : {v}", scope=scope_name)
            else:
                pin.put_input(component_name, label=display_name, value=v, scope=scope_name)
    
    # 展示inf型项
    def _show_int(self, doc_items, component_name, display_name, scope_name, v):
        if doc_items:
            pin.put_select(component_name,
                            [{"label": i, "value": i} for i in doc_items], value=v,
                            label=display_name,
                            scope=scope_name)
        else:
            if "collection_log.json" in self.file_name:
                output.put_text(f"{display_name} : {v}", scope=scope_name)
            else:
                pin.put_input(component_name, label=display_name, value=v, scope=scope_name, type='number')