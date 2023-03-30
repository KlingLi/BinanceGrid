# -*- coding: utf-8 -*-
# @Time : 2022/11/2 21:36
# @Author : 
# @File : futures_grid.py 
# @Software: PyCharm
"""
简单的等差网格策略实现，使用http request 请求

在撒网初始撒网不超出边界时，该程序适用（中频及以下）
自动获取合约交易规则信息，并且读取txt以输入参数
"""
import re
import time
from calc import calc
from logger import LogRecorder
import binance.client
from binance.client import Client


def price_num_validator(price_num: float) -> bool:
    # 判断价格是否是该合约价格精度的整数倍    # todo: 完整的filter，上下限，精度等等
    if calc(price_num, price_precision, '%') == 0:
        return True
    else:
        return False


def quantity_num_validator(quantity_num: float) -> bool:
    # 判断数量是否为精度的整数倍
    if calc(quantity_num, quantity_precision, '%') == 0:
        return True
    else:
        return False


def grid_var_normalization(up_limit, down_limit, price_step, grid_num):
    # 判断并修正网格参数，使其满足下单需求
    modified_up_limit = up_limit
    modified_down_limit = down_limit
    modified_price_step = price_step
    modified_grid_num = grid_num
    # 此时已判断价格上下限的精度合理性
    if modified_grid_num is not None:
        temp_price_step = calc((calc(modified_up_limit, modified_down_limit, '-')), modified_grid_num, '/')
        if price_num_validator(temp_price_step):
            # 网格数量决定的价格跳变合理，可以输出
            modified_price_step = temp_price_step
        else:
            # 默认使网格数量更少，取精度允许的更高价格跳变
            modified_price_step = calc(calc(price_precision, int(calc(modified_price_step, price_precision, '/')), '*'), price_precision, '+')

    elif modified_price_step is not None:
        if not price_num_validator(modified_price_step):
            trading_recorder.log_print('价格跳变不合理，超出可允许的精度')
            modified_price_step = calc(calc(price_precision, int(calc(modified_price_step, price_precision, '/')), '*'), price_precision, '+')
            trading_recorder.log_print('修改为: {}'.format(str(modified_price_step)))
    else:
        trading_recorder.log_print('输入网格参数不足')
        trading_recorder.exit_program()

    modified_grid_num = int(int(calc(calc(modified_up_limit, modified_down_limit, '-'), price_precision, '/')) / int(calc(modified_price_step, price_precision, '/')))
    modified_up_limit = calc(modified_down_limit, calc(modified_grid_num, modified_price_step, '*'), '+')
    modified_grid_num += 1

    return modified_up_limit, modified_down_limit, modified_price_step, modified_grid_num


def generate_order_list(order_side: str, quantity: float, price_list: list) -> list:
    """
    生成 batch_order 的参数
    :param order_side:
    :param quantity:
    :param price_list:
    :return:
    """
    batch_order_list = []
    if order_side == 'BUY':
        batch_order_list = [
            {
                'symbol': trading_object,
                'side': 'BUY',
                'type': 'LIMIT',
                'quantity': str(quantity),
                'timeInForce': 'GTC',
                'price': str(price),
            } for price in price_list
        ]
    elif order_side == 'SELL':
        batch_order_list = [
            {
                'symbol': trading_object,
                'side': 'SELL',
                'type': 'LIMIT',
                'quantity': str(quantity),
                'timeInForce': 'GTC',
                'price': str(price),
            } for price in price_list
        ]
    else:
        pass

    return batch_order_list


def quit_trading(current_client: binance.client.Client):
    """
    完全退出交易，
    操作：撤销所有挂单，并平掉所有仓位。
    :param current_client: 当前交易api
    :return:
    """
    return
    cancel_order_res = current_client.futures_cancel_all_open_orders(symbol=trading_object)
    if cancel_order_res['code'] == 200:
        # 撤销挂单成功
        trading_recorder.log_print('已撤销所有挂单. server msg: {}'.format(cancel_order_res['msg']))
    else:
        trading_recorder.log_print('撤销挂单失败，需手动操作。 server msg: {}'.format(cancel_order_res['msg']))

    try:
        buy_close_res = current_client.futures_create_order(
            symbol=trading_object,
            side='BUY',
            type='MARKET',
            reduceOnly='true',
            quantity=max_market_quantity,
        )
        if 'code' in buy_close_res.keys():
            trading_recorder.log_print('买平仓失败，msg: {}'.format(buy_close_res['msg']))  # todo: 检验该挂单真实成交情况
        else:
            trading_recorder.log_print('成功市价买平仓，数量 {}'.format(buy_close_res['origQty']))
            return
    except Exception:  # todo: import API exception
        pass

    try:
        buy_close_res = current_client.futures_create_order(
            symbol=trading_object,
            side='SELL',
            type='MARKET',
            reduceOnly='true',
            quantity=max_market_quantity,
        )
        if 'code' in buy_close_res.keys():
            trading_recorder.log_print('卖平仓失败，msg: {}'.format(buy_close_res['msg']))
        else:
            trading_recorder.log_print('成功市价卖平仓，数量 {}'.format(buy_close_res['origQty']))
            return
    except Exception:
        pass


def get_certain_exchange_info(symbol_name: str, client) -> dict:
    all_info = client.futures_exchange_info()

    for each_symbol_info in all_info['symbols']:
        if each_symbol_info['symbol'] == symbol_name:
            return dict(each_symbol_info)


api_key = 'your_api_key'
api_secret = 'your_api_secret'

trading_recorder = LogRecorder()
trading_recorder.open_file('trading_logs_1')
trading_recorder.log_print('开始记录')

# read grid params from txt
params_file = open('grid_params_1.txt', 'r', encoding='utf-8')
params_content = params_file.read()
params_file.close()

trading_client = Client(api_key, api_secret)
# 设置交易品种 及其规则
trading_object = re.findall(r'symbol_name=(.*?)\n', params_content)[0].replace(' ', '')
# get symbol exchange rules
trading_rules_dict = get_certain_exchange_info(trading_object, trading_client)
trading_recorder.log_print(trading_rules_dict['filters'][0])  # todo: delete
price_precision = float(trading_rules_dict['filters'][0]['tickSize'])
quantity_precision = float(trading_rules_dict['filters'][1]['stepSize'])
max_market_quantity = float(trading_rules_dict['filters'][2]['maxQty'])
# todo: delete test print
# trading_recorder.log_print('price_precision:{}\nquantity_precision:{}\nmax_lot_quantity:{}\n'.format(price_precision, quantity_precision, max_market_quantity))

if __name__ == '__main__':
    actual_trading = True
    # ##===================== initial settings =====================## #
    # 网格方向(多，空，中性网格)
    grid_side = re.findall(r'grid_side=(.*?)\n', params_content)[0].replace(' ', '')
    # 网格上下限价格               # todo: 网格上限高于下限判断
    grid_upper_limit = float(re.findall(r'upper_limit=(.*?)\n', params_content)[0].replace(' ', ''))
    grid_down_limit = float(re.findall(r'down_limit=(.*?)\n', params_content)[0].replace(' ', ''))
    # 设置网格触发退出价格        # todo: 该价格与开始撒网时可能会冲突，需合理化范围
    grid_quit_price = float(re.findall(r'quit_price=(.*?)\n', params_content)[0].replace(' ', ''))
    # 网格跳变价格或数量，三选一，todo:跳变价格需要高于手续费 maker/taker
    grid_price_absolute_step = float(re.findall(r'price_step=(.*?)\n', params_content)[0].replace(' ', ''))
    grid_price_percent_step = None
    grid_total_num = None
    # 设置网格每单交易量
    # todo: notion and precision
    grid_each_quantity = float(re.findall(r'each_quantity=(.*?)\n', params_content)[0].replace(' ', ''))
    # 设置网格策略开始时，成交多少比例的多单(空单)，100 % 则表示完全看多(看空)，0 % 则表示中性网格，二选一
    grid_initial_trade_ratio = float(re.findall(r'ini_trade_ratio=(.*?)\n', params_content)[0].replace(' ', ''))
    grid_convergence_price = None

    # 设置账户杠杆    todo: set leverage
    set_account_leverage = int(re.findall(r'account_leverage=(.*?)\n', params_content)[0].replace(' ', ''))
    # ##===================== initialization end  =====================## #
    # todo: test print to be deleted
    # trading_recorder.log_print('grid_side:{}\nup_limit:{}\ndown_limit:{}\nquit_price:{}\nprice_step:{}\neach_quantity:{}\nratio:{}\nleverage:{}\n'.format(
    #     grid_side, grid_upper_limit, grid_down_limit, grid_quit_price, grid_price_absolute_step, grid_each_quantity, grid_initial_trade_ratio, set_account_leverage))

    # trading_recorder.exit_program()

    try:
        # input normalization
        if not (price_num_validator(grid_upper_limit) and price_num_validator(grid_down_limit)):
            trading_recorder.log_print('价格上下限数字不合理，超出可允许的精度')
            trading_recorder.exit_program()

        if not quantity_num_validator(grid_each_quantity):
            trading_recorder.log_print('交易数量设置不合理，不符合要求精度，数量精度为: {}'.format(str(quantity_precision)))
            trading_recorder.exit_program()

        grid_upper_limit, grid_down_limit, grid_price_absolute_step, grid_total_num = \
            grid_var_normalization(grid_upper_limit, grid_down_limit, grid_price_absolute_step, grid_total_num)

        trading_recorder.log_print('网格上限：{}\n网格下限：{}\n网格跳变价格：{}\n网格数量：{}\n'.format
                                   (str(grid_upper_limit), str(grid_down_limit), str(grid_price_absolute_step), str(grid_total_num)))

        grid_each_quantity = float(grid_each_quantity)
        # normalization end
        all_grid_price = tuple(calc(grid_down_limit, calc(grid_price_absolute_step, i, '*'), '+') for i in range(grid_total_num))
        # trading_recorder.log_print(all_grid_price)
        if not actual_trading:
            trading_recorder.log_print(all_grid_price)
            trading_recorder.exit_program()

        leverage_response = trading_client.futures_change_leverage(symbol=trading_object, leverage=set_account_leverage)
        if leverage_response['symbol'] == trading_object:
            trading_recorder.log_print('账户杠杆成功设置为 {}x'.format(str(set_account_leverage)))

        # ##===== 第一步，撒网，市价成交一定数量买(卖)单，上下挂一定数量买卖单并验证成功 =====## #
        pending_order_num = 20
        open_buy_orders = [{'price': 0, 'orderId': None, 'status': None}]
        open_sell_orders = [{'price': 0, 'orderId': None, 'status': None}]
        # 首先市价下单一定数量，完成后检查价格
        ini_order_quantity = 0
        trading_recorder.log_print(trading_client.get_server_time())        # todo: transfer timestamp
        current_price = float(trading_client.futures_symbol_ticker(symbol=trading_object)['price'])
        trading_recorder.log_print('当前合约价格: {}'.format(current_price))
        if not (grid_down_limit < current_price < grid_upper_limit):  # todo: grid_down_limit == current_price
            trading_recorder.log_print('当前价格不在网格范围内')
            trading_recorder.exit_program()

        critical_index = 0  # todo: more efficient algorithm
        for each_index, each_grid_price in enumerate(all_grid_price):
            if each_grid_price <= current_price < (each_grid_price + grid_price_absolute_step):
                if current_price - each_grid_price <= grid_price_absolute_step / 2:
                    critical_index = each_index
                else:
                    critical_index = each_index + 1
        trading_recorder.log_print('critical index = {}'.format(critical_index))
        # 开始网格策略时，each_index 网格不挂单，critical_index 表示当前价格在其 ±1 区间范围内
        ini_market_order_res = None
        if grid_initial_trade_ratio > 0:
            if grid_side == 'BUY':  # todo: 其他字符表示中性网格
                ini_order_quantity = calc(grid_each_quantity, round(grid_initial_trade_ratio * critical_index), '*')
                ini_market_order_res = trading_client.futures_create_order(
                    symbol=trading_object,
                    side=trading_client.SIDE_BUY,
                    type=trading_client.ORDER_TYPE_MARKET,
                    quantity=ini_order_quantity  # todo: min(quantity, 1)
                )
            elif grid_side == 'SELL':
                ini_order_quantity = calc(grid_each_quantity, round(grid_initial_trade_ratio * (grid_total_num - critical_index - 1)), '*')
                ini_market_order_res = trading_client.futures_create_order(
                    symbol=trading_object,
                    side=trading_client.SIDE_SELL,
                    type=trading_client.ORDER_TYPE_MARKET,
                    quantity=ini_order_quantity
                )

            ini_order_id = ini_market_order_res['orderId']
            while True:
                time.sleep(0.3)  # todo:短短时间内可能发生任何情况，需判断
                ini_order_status = trading_client.futures_get_order(symbol=trading_object, orderId=ini_order_id)
                if ini_order_status['status'] == 'FILLED':
                    trading_recorder.log_print('市价成交，成交量：{} 成交均价：{}'.format(ini_order_status['executedQty'], ini_order_status['avgPrice']))
                    break
                else:
                    trading_recorder.log_print('暂未成交，等待重新查询。。')

        # 开始挂单撒网    todo: 异步函数提高效率！！！！！
        trading_recorder.log_print('开始撒网')  # todo: 撒网不超过边界，暂未判断
        ini_limit_buy_price_list = list(all_grid_price[max(0, (critical_index - pending_order_num)):critical_index])
        ini_limit_sell_price_list = list(all_grid_price[critical_index + 1:critical_index + pending_order_num + 1])
        trading_recorder.log_print(ini_limit_buy_price_list, '\n', ini_limit_sell_price_list, '\n')

        open_buy_orders = [{'price': each_price, 'orderId': None, 'status': None} for each_price in ini_limit_buy_price_list]
        open_sell_orders = [{'price': each_price, 'orderId': None, 'status': None} for each_price in ini_limit_sell_price_list]
        # trading_recorder.log_print(open_buy_orders, '\n', open_sell_orders, '\n')

        # 从 critical index 开始向两边撒网
        for index, temp_status in enumerate(open_sell_orders):
            # 下单后，解析response, 保存每一单的id
            # todo:此处假设batch_order返回的列表与发出的列表为相同的顺序，可以优化
            each_buy_order_params = generate_order_list('BUY', grid_each_quantity, [open_buy_orders[-(index + 1)]['price']])
            each_sell_order_params = generate_order_list('SELL', grid_each_quantity, [open_sell_orders[index]['price']])
            each_ini_response = trading_client.futures_place_batch_order(batchOrders=(each_buy_order_params + each_sell_order_params))

            each_ini_buy_res, each_ini_sell_res = each_ini_response[0], each_ini_response[1]
            if 'code' in each_ini_buy_res.keys():
                # 该挂单失败
                trading_recorder.log_print('{} 价位的多单 挂单失败\ncode: {}\nmsg: {}\n'.format
                                           (str(open_buy_orders[-(index + 1)]['price']), str(each_ini_buy_res['code']), each_ini_buy_res['msg']))
                # todo:失败挂单重新挂单，否则后续程序出问题
                trading_recorder.exit_program()
            else:
                # 挂单成功，保存 order id 和 status
                if not (open_buy_orders[-(index + 1)]['price'] == float(each_ini_buy_res['price'])):  # todo: delete
                    trading_recorder.log_print('多单顺序没有一一对应')
                    trading_recorder.exit_program()
                open_buy_orders[-(index + 1)]['orderId'] = each_ini_buy_res['orderId']
                open_buy_orders[-(index + 1)]['status'] = each_ini_buy_res['status']

            if 'code' in each_ini_sell_res.keys():
                # 该挂单失败
                trading_recorder.log_print('{} 价位的空单 挂单失败\ncode: {}\nmsg: {}\n'.format
                                           (str(open_sell_orders[index]['price']), str(each_ini_sell_res['code']), each_ini_sell_res['msg']))
                trading_recorder.exit_program()
            else:
                # 挂单成功，保存 order id 和 status
                if not (open_sell_orders[index]['price'] == float(each_ini_sell_res['price'])):
                    trading_recorder.log_print('空单顺序没有一一对应')
                    trading_recorder.exit_program()
                open_sell_orders[index]['orderId'] = each_ini_sell_res['orderId']
                open_sell_orders[index]['status'] = each_ini_sell_res['status']
        # 撒网完成
        trading_recorder.log_print(open_buy_orders, '\n', open_sell_orders, '\n')
        # current_price = trading_client.futures_symbol_ticker(symbol=trading_object)['price']

        # ##===== 第二步，不断检测最近的买卖单成交状况，随市场波动不断维护挂单 =====## #
        # todo: 异步函数提高效率！！！
        # todo: 假设不存在跳跃网格成交的情况
        filled_buy_order_num, filled_sell_order_num = 0, 0
        this_buy_order_res, this_sell_order_res = '', ''
        while True:
            # 首先查询最近买卖单地成交情况
            filled_buy_order_num, filled_sell_order_num = 0, 0
            current_min_pending_order_num = min(len(open_buy_orders), len(open_sell_orders))
            for index in range(current_min_pending_order_num):
                this_buy_order_res = trading_client.futures_get_order(symbol=trading_object, orderId=open_buy_orders[-(index + 1)]['orderId'])
                this_sell_order_res = trading_client.futures_get_order(symbol=trading_object, orderId=open_sell_orders[index]['orderId'])

                if this_buy_order_res['status'] == 'FILLED':
                    filled_buy_order_num += 1
                    trading_recorder.log_print('检测到 {} 价位的 买{} 挂单成交'.format(this_buy_order_res['price'], str(index + 1)))
                elif this_sell_order_res['status'] == 'FILLED':
                    filled_sell_order_num += 1
                    trading_recorder.log_print('检测到 {} 价位的 卖{} 挂单成交'.format(this_sell_order_res['price'], str(index + 1)))
                elif (this_buy_order_res['status'] == 'NEW') and (this_sell_order_res['status'] == 'NEW'):
                    # 两边均未成交，继续等待，检测
                    time.sleep(0.20)  # 每一次检测间隔时间 todo: 检验报单次数与频率
                    break
                else:
                    pass

                if index == current_min_pending_order_num - 1:
                    # 某一方向(或两边)所有挂单被击穿，行情很剧烈，需要报警
                    trading_recorder.log_print('单边所有挂单被击穿，出现极端行情，或者已经达到网格边界，撤销所有订单')
                    trading_recorder.log_print(time.strftime("%Y-%m-%d -- %H:%M:%S", time.localtime()), '\n\n')
                    quit_trading(trading_client)
                    trading_recorder.exit_program()  # todo: 单边极端行情处理

            # 根据买卖挂单成交情况 补充挂单 todo:边界管理
            if (filled_buy_order_num + filled_sell_order_num) == 0:
                # 没有挂单成交
                pass
            else:
                # 存在成交挂单
                if (filled_buy_order_num == 0) or (filled_sell_order_num == 0):
                    # 成交单边挂单，理想情况
                    if filled_buy_order_num:
                        # 维护卖单挂单
                        for each_post_index in range(filled_buy_order_num):
                            each_sell_post_price = all_grid_price[critical_index - each_post_index]
                            # 若达到触发价格，退出网格交易
                            if (grid_quit_price - grid_price_absolute_step) < each_sell_post_price < (grid_quit_price + grid_price_absolute_step):
                                trading_recorder.log_print('达到触发停止价格，停止网格策略')
                                quit_trading(trading_client)
                                trading_recorder.exit_program()
                            # 增添新挂单直到成功为止
                            while True:
                                trading_recorder.log_print('在 {} 价位挂卖单'.format(str(each_sell_post_price)))
                                each_sell_post_param = generate_order_list('SELL', grid_each_quantity, [each_sell_post_price])
                                each_sell_post_res = trading_client.futures_place_batch_order(batchOrders=each_sell_post_param)[0]
                                if 'code' in each_sell_post_res.keys():
                                    trading_recorder.log_print(' {} 价位的卖单 挂单失败\ncode: {}, msg: {}\n尝试重新挂单'.format
                                                               (str(each_sell_post_price), str(each_sell_post_res['code']), each_sell_post_res['msg']))
                                    continue
                                else:
                                    # 卖单挂单成功，保存id
                                    trading_recorder.log_print(' {} 价位 卖单 挂单成功'.format(each_sell_post_res['price']))
                                    open_sell_orders.insert(0, {'price': each_sell_post_price, 'orderId': each_sell_post_res['orderId'], 'status': each_sell_post_res['status']})
                                    break

                            if (critical_index - each_post_index - pending_order_num - 1) >= 0:
                                # 没有到达网格下边界，增添买单
                                each_buy_post_price = all_grid_price[critical_index - each_post_index - pending_order_num - 1]
                                while True:
                                    trading_recorder.log_print('在 {} 价位挂买单'.format(str(each_buy_post_price)))
                                    each_buy_post_param = generate_order_list('BUY', grid_each_quantity, [each_buy_post_price])
                                    each_buy_post_res = trading_client.futures_place_batch_order(batchOrders=each_buy_post_param)[0]
                                    if 'code' in each_buy_post_res.keys():
                                        trading_recorder.log_print(' {} 价位的买单 挂单失败\ncode: {}, msg: {}\n尝试重新挂单'.format
                                                                   (str(each_buy_post_price), str(each_buy_post_res['code']), each_buy_post_res['msg']))
                                        continue
                                    else:
                                        # 买单挂单成功，保存id
                                        trading_recorder.log_print(' {} 价位 买单 挂单成功'.format(each_buy_post_res['price']))
                                        open_buy_orders.insert(0, {'price': each_buy_post_price, 'orderId': each_buy_post_res['orderId'], 'status': each_buy_post_res['status']})
                                        break

                            # 撤销多余挂单
                            try:
                                trading_recorder.log_print('撤销 {} 价位的 卖单挂单，订单号 {}'.format(str(open_sell_orders[-1]['price']), str(open_sell_orders[-1]['orderId'])))
                                each_cancel_res = trading_client.futures_cancel_order(symbol=trading_object, orderId=open_sell_orders[-1]['orderId'])
                                open_sell_orders.pop(-1)
                            except Exception:  # todo: import BinanceAPIException:
                                trading_recorder.log_print('撤单失败')
                            open_buy_orders.pop(-1)

                        critical_index -= filled_buy_order_num

                    elif filled_sell_order_num:
                        # 维护买单挂单
                        for each_post_index in range(filled_sell_order_num):
                            each_buy_post_price = all_grid_price[critical_index + each_post_index]
                            # 若达到触发价格，退出网格交易
                            if (grid_quit_price - grid_price_absolute_step) < each_buy_post_price < (grid_quit_price + grid_price_absolute_step):
                                trading_recorder.log_print('达到触发停止价格，停止网格策略')
                                quit_trading(trading_client)
                                trading_recorder.exit_program()
                            while True:
                                trading_recorder.log_print('在 {} 价位挂买单'.format(str(each_buy_post_price)))
                                each_buy_post_param = generate_order_list('BUY', grid_each_quantity, [each_buy_post_price])
                                each_buy_post_res = trading_client.futures_place_batch_order(batchOrders=each_buy_post_param)[0]
                                if 'code' in each_buy_post_res.keys():
                                    trading_recorder.log_print(' {} 价位的买单 挂单失败\ncode: {}, msg: {}\n尝试重新挂单'.format
                                                               (str(each_buy_post_price), str(each_buy_post_res['code']), each_buy_post_res['msg']))
                                    continue
                                else:
                                    # 买单挂单成功，保存id, 并删除多余挂单
                                    trading_recorder.log_print(' {} 价位 买单 挂单成功'.format(each_buy_post_res['price']))
                                    open_buy_orders.append({'price': each_buy_post_price, 'orderId': each_buy_post_res['orderId'], 'status': each_buy_post_res['status']})
                                    break

                            if (critical_index + each_post_index + pending_order_num + 2) <= grid_total_num:
                                # 没有到达网格上边界，增添卖单
                                each_sell_post_price = all_grid_price[critical_index + each_post_index + pending_order_num + 1]
                                while True:
                                    trading_recorder.log_print('在 {} 价位挂卖单'.format(str(each_sell_post_price)))
                                    each_sell_post_param = generate_order_list('SELL', grid_each_quantity, [each_sell_post_price])
                                    each_sell_post_res = trading_client.futures_place_batch_order(batchOrders=each_sell_post_param)[0]
                                    if 'code' in each_sell_post_res.keys():
                                        trading_recorder.log_print(' {} 价位的卖单 挂单失败\ncode: {}, msg: {}\n尝试重新挂单'.format
                                                                   (str(each_sell_post_price), str(each_sell_post_res['code']), each_sell_post_res['msg']))
                                        continue
                                    else:
                                        # 卖单挂单成功，保存id
                                        trading_recorder.log_print(' {} 价位 卖单 挂单成功'.format(each_sell_post_res['price']))
                                        open_sell_orders.append({'price': each_sell_post_price, 'orderId': each_sell_post_res['orderId'], 'status': each_sell_post_res['status']})
                                        break

                            try:
                                trading_recorder.log_print('撤销 {} 价位的 买单挂单，订单号 {}'.format(str(open_buy_orders[0]['price']), str(open_buy_orders[0]['orderId'])))
                                each_cancel_res = trading_client.futures_cancel_order(symbol=trading_object, orderId=open_buy_orders[0]['orderId'])
                                open_buy_orders.pop(0)
                            except Exception:  # todo: import BinanceAPIException:
                                trading_recorder.log_print('撤单失败')
                            open_sell_orders.pop(0)

                        critical_index += filled_sell_order_num

                else:
                    # 两边挂单都有成交，行情较剧烈
                    trading_recorder.log_print('行情较剧烈，施工中。。。。开摆')
                    quit_trading(trading_client)
                    trading_recorder.exit_program()
                    pass

                trading_recorder.log_print('\n当前买单挂单数量：{}，卖单挂单数量{}'.format(str(len(open_buy_orders)), str(len(open_sell_orders))))
                trading_recorder.log_print(time.strftime("%Y-%m-%d -- %H:%M:%S", time.localtime()), '\n\n')

        # end todo:cancel all orders

    except Exception as e:
        trading_recorder.log_print(time.strftime("%Y-%m-%d -- %H:%M:%S", time.localtime()), '\n\n')
        trading_recorder.log_print('程序出错，错误原因：\n', e)
        quit_trading(trading_client)
        trading_recorder.exit_program()
