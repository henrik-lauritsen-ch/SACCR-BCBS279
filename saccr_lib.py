import pandas as pd
from math import exp, e, log, sqrt, isnan
import scipy.stats as s
pd.options.mode.chained_assignment = None


def Multiplier(v, c, add_on_agg):
    floor = 0.05    
    return min(1.0, floor + (1.0 - floor)*exp((v - c)/(2*(1.0 - floor)*add_on_agg)))


def PFE(multiplier, add_on_agg):
    return multiplier*add_on_agg


def ReplacementCosts(v, c):
    # v = market_value_derivatives
    # c = collateral
    return max(v - c, 0)


def EAD(rc, pfe):
    return 1.4*(rc + pfe)

  
def SupervisoryDuration(asset_type, s, e):
    sd = 1.0
    if asset_type in (1, 3):
        sd = (exp(-0.05*s) - exp(-0.05*e))/0.05
    return sd


def CalcM(asset_type, product_type, settlement_type, maturity, underlying_tenor):    
    if asset_type in (1, 3):
        #IR + CR
        if product_type == 'OPT':
            if settlement_type == 'CASH':
                m = maturity
            else:
                m = maturity + underlying_tenor
        else:
            m = maturity
    else: 
        #FX. EQ and COM
        if product_type == 'OPT':
            m = maturity #+ underlying_tenor
        else:
            m = maturity        
    return m


def CalcE(asset_type, product_type, maturity, underlying_tenor): 
    if asset_type in (1, 3):
        if product_type == 'OPT':
            _e = maturity + underlying_tenor
        else:
            _e = maturity
    else:
        _e = 'NaN'
    return _e


def CalcS(asset_type, product_type, maturity):
    if asset_type in (1, 3):
        if product_type == 'OPT':
            s = maturity
        else:
            s = 0        
    else:
        s = 'NaN'
    return s


def CalcT(product_type, maturity):
    if product_type == 'OPT':
        t = maturity
    else:
        t = 'NaN'
    return t


def MaturityFactor(maturity):
    return max(14/365.0, sqrt(min(maturity, 1.0)))


def AssetType(asset_txt):
    asset_type = 0
    if asset_txt == 'IR':
        asset_type = 1
    elif asset_txt == 'FX':
        asset_type = 2
    elif asset_txt == 'CR':
        asset_type = 3
    elif asset_txt == 'EQ':
        asset_type = 4
    elif asset_txt == 'CO':
        asset_type = 5
    return asset_type


def TimeBucketsIR(asset_class, _e):
    if asset_class == 1:
        if _e < 1.0:
            tb = 'E1'
        elif _e <= 5.0:
            tb = 'E15'
        else:
            tb = 'E5'
    else:
        tb = 'NaN'
    return tb


def AdjustedNotional(asset_type, supervisory_duration, 
                      notional_rec_leg_dom, notional_pay_leg_dom,    
                      ccy_rec_leg, ccy_pay_leg,
                      domestic_currency,
                      num_contracts, price):
    an = 0
    is_rec_leg_dom = False
    is_pay_leg_dom = False
    
    if ccy_rec_leg == domestic_currency:
        is_rec_leg_dom = True
    elif ccy_pay_leg == domestic_currency:
        is_pay_leg_dom = True
    
    if asset_type in (1, 3):
        #IR or CREDIT
        an = supervisory_duration*notional_rec_leg_dom
    elif asset_type == 2:
        #FX
        if is_rec_leg_dom:
            an = notional_pay_leg_dom
        elif is_pay_leg_dom:
            an = notional_rec_leg_dom
        else:
            an = max(notional_rec_leg_dom, notional_pay_leg_dom)
    elif asset_type in (4, 5):
        #Equity or Commodity
        an = num_contracts*price
    else:
        an = notional_rec_leg_dom
    return an


def SwitchFXCross(asset_type, ccy1, ccy2):
    sfxc = 'NaN'
    if asset_type == 2:
        if ccy1 > ccy2:
            sfxc = True
        else:
            sfxc = False
    return sfxc


def SwitchFXOptionType(asset_type, switch_fx, product_type, call_put):
    applied_call_put = call_put
    if asset_type == 2 and switch_fx == True and product_type == 'OPT':
        if call_put == 'C':
            applied_call_put = 'P'
        else:
            applied_call_put = 'C'
    return applied_call_put


def SwitchFXBuySell(asset_type, product_type, fx_hs_ccy, ccy_receive_Leg, ccy_pay_Leg, buy_sell):
    applied_buy_sell = buy_sell
    if (asset_type == 2 and product_type != 'OPT'):
        if fx_hs_ccy == ccy_receive_Leg + ccy_pay_Leg:
            applied_buy_sell = 'B'
        else:
            applied_buy_sell = 'S'
    return applied_buy_sell


def GetSigma(asset_type, underlying_asset):
    if asset_type == 1:
        sigma = 0.5
    elif asset_type == 2:
        sigma = 0.15
    elif asset_type == 3:
        if underlying_asset == 'INDEX':
            sigma = 0.8
        else:
            sigma = 1.0
    elif asset_type == 4:
        if underlying_asset == 'INDEX':
            sigma = 0.75
        else:
            sigma = 1.2
    elif asset_type == 5:
        if underlying_asset == 'EL':
            sigma = 1.5
        else:
            sigma = 0.7
    else:
        sigma = 1.0
    return sigma


def GetCorrelation(asset_type, underlying_asset):
    corr = 'NaN'
    if asset_type == 3:
        if underlying_asset in ('IG','SG'):
            corr = 0.8
        else:
            corr = 0.5
    elif asset_type == 4:
        if underlying_asset == 'INDEX':
            corr = 0.8
        else:
            corr = 0.5
    elif asset_type == 5:
        corr = 0.4
    return corr


def GetSF(asset_type, credit_rating, underlying_asset):
    if asset_type == 1:
        sf = 0.005
    elif asset_type == 2:
        sf = 0.04
    elif asset_type == 3:
        if credit_rating in ('AA','AAA'):
            sf = 0.0038
        elif credit_rating == 'A':
            sf = 0.0042
        elif credit_rating == 'BBB':
            sf = 0.0054
        elif credit_rating == 'BB':
            sf = 0.0106
        elif credit_rating == 'B':
            sf = 0.016
        elif credit_rating == 'CCC':
            sf = 0.06
        elif underlying_asset == 'IG':
            sf = 0.0038
        elif underlying_asset == 'SG':
            sf = 0.0106
        else:
            sf = 0.06    
    elif asset_type == 4:
        if underlying_asset == 'INDEX':
            sf = 0.2
        else:
            sf = 0.32
    elif asset_type == 5:
        if underlying_asset == 'ELECTRICITY':
            sf = 0.4
        else:
            sf = 0.18
    else:
        sf = 0.4
    return sf



def SaccrDelta(asset_type, product_type, underlying_asset, applied_buy_sell, applied_call_put, underlying_price, underlying_strike, option_maturity, fx_hs_ccy, underlying_quoted_ccy):
    
    if product_type == 'OPT':        
        sigma = GetSigma(asset_type, underlying_asset)
        if (isnan(underlying_price) or underlying_price == 0) or (isnan(underlying_strike) or underlying_strike == 0):
            strike = 1.0
            spot = 1.0    
        
        if (isnan(option_maturity) or option_maturity == 0):
            option_maturity = 1.0
        
        if (fx_hs_ccy != underlying_quoted_ccy and asset_type==2):
            spot = 1.0/underlying_price
            strike = 1.0/underlying_strike
        else:
            spot = underlying_price
            strike = underlying_strike
        
        cp_sign = 1
        bs_sign = 1
        if applied_call_put == 'P':
            cp_sign = -1
        if applied_buy_sell == 'S':
            bs_sign = -1
            
        d1 = (log(spot/strike) + 0.5*option_maturity*sigma**2)/(sigma*sqrt(option_maturity))
        delta = cp_sign*bs_sign*s.norm.cdf(cp_sign*d1)
        
    else:
        if applied_buy_sell.upper() == 'B':
            delta = 1.0
        else:
            delta = -1.0
    return delta


def CalcAddOnAC(corr_term, _1m_corr_term):
    return sqrt(pow(corr_term, 2) + _1m_corr_term)

def IrEffectiveNotional(d1, d2, d3):
    return sqrt(d1**2 + d2**2 + d3**2 + 1.4*d1*d2 + 1.4*d2*d3 + 0.6*d1*d3)