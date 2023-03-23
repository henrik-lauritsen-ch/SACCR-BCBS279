####################################################################################################
# Import libraries
import pandas as pd
import numpy as np
import saccr_lib as sl

  
####################################################################################################
# Set input file 'location' and 'name'
file_location = '/Users/henriklauritsen/Documents/GitHub/SACCR/'
file_name = 'test2_data.csv'


####################################################################################################
# Read base data
df = pd.read_csv(file_location + file_name)

  
####################################################################################################
# PART 1: Cacl basic SACCR input
""" 1. AssetType """
df['Asset_Type'] = df.apply(lambda row: sl.AssetType(row['Asset_Class']), axis=1)

""" 2. Calc Notionals in Domestic Currency """
df['Not_Rec_Leg_Dom'] = df['Notional_Receive_Leg']
df['Not_Pay_Leg_Dom'] = df['Notional_Pay_Leg']
com_eq = (df['Asset_Type'] >= 4 )

""" 3. Calc M, S, E, T """
df['M'] = df.apply(lambda row: sl.CalcM(row['Asset_Type'], row['Product_Type'], row['Settlement_Type'], row['Maturity'], row['Underlying_Tenor']), axis = 1)
df['S'] = df.apply(lambda row: sl.CalcS(row['Asset_Type'], row['Product_Type'], row['Maturity']), axis = 1)
df['E'] = df.apply(lambda row: sl.CalcE(row['Asset_Type'], row['Product_Type'], row['Maturity'], row['Underlying_Tenor']), axis = 1)
df['T'] = df.apply(lambda row: sl.CalcT(row['Product_Type'], row['Maturity']), axis = 1)

""" 4. SupervisoryDuration """
df['SD'] = df.apply(lambda row: sl.SupervisoryDuration(row['Asset_Type'], row['S'], row['E']), axis = 1)

""" 5. AdjustedNotional """
df['AdjustedNotional'] = df.apply(lambda row: sl.AdjustedNotional(row['Asset_Type'], 
                                                                  row['SD'], 
                                                                  row['Not_Rec_Leg_Dom'], row['Not_Pay_Leg_Dom'], 
                                                                  row['CCY_Receive_Leg'], row['CCY_Pay_Leg'], 'CHF', 
                                                                  row['Number_of_Contracts'], row['Market_Price']), axis = 1)

""" 6. MF """
df['MF'] = df.apply(lambda row: sl.MaturityFactor(row['M']), axis = 1)

""" 7. Build Hedge Set """
#Hedge = Netting_Set_Id + Asset Class + Currency/Name + Maturity Bucket (last only for IR)
ir_set = (df['Asset_Type'] == 1)
fx_set = (df['Asset_Type'] == 2)
cr_set = (df['Asset_Type'] == 3)
eq_set = (df['Asset_Type'] == 4)
co_set = (df['Asset_Type'] == 5)
df['IR_Time_Bucket'] = df.apply(lambda row: sl.TimeBucketsIR(row['Asset_Type'], row['E']), axis = 1)


# Hedge set Id for IR, EQ, CO and CR:
df.loc[ir_set, 'Hedge_Set_Id'] = df.loc[ir_set, 'Netting_Set'] + '_' + df.loc[ir_set, 'Asset_Class'] + '_' + df.loc[ir_set, 'CCY_Receive_Leg'] # + '_' + df['IR_Time_Bucket']
df.loc[eq_set, 'Hedge_Set_Id'] = df.loc[eq_set, 'Netting_Set'] + '_' + df.loc[eq_set, 'Asset_Class'] + '_' + df.loc[eq_set, 'Underlying_ID']
df.loc[co_set, 'Hedge_Set_Id'] = df.loc[co_set, 'Netting_Set'] + '_' + df.loc[co_set, 'Asset_Class'] + '_' + df.loc[co_set, 'Commodity_Type']
df.loc[cr_set, 'Hedge_Set_Id'] = df.loc[cr_set, 'Netting_Set'] + '_' + df.loc[cr_set, 'Asset_Class'] + '_' + df.loc[cr_set, 'Underlying_ID']

# Hedge set for FX:
df.loc[fx_set, 'Switch_FX'] = df.apply(lambda row: sl.SwitchFXCross(row['Asset_Type'], row['CCY_Receive_Leg'], row['CCY_Pay_Leg']), axis = 1)
fx_set_switch = (df['Switch_FX'] == True)
fx_set_no_switch = (df['Switch_FX'] == False)
df.loc[fx_set_switch, 'FX_HS_CCY'] = df.loc[fx_set_switch, 'CCY_Pay_Leg'] + df.loc[fx_set_switch, 'CCY_Receive_Leg']
df.loc[fx_set_no_switch, 'FX_HS_CCY'] = df.loc[fx_set_no_switch, 'CCY_Receive_Leg'] + df.loc[fx_set_no_switch, 'CCY_Pay_Leg']
df.loc[fx_set, 'Hedge_Set_Id'] = df.loc[fx_set,'Netting_Set'] + '_' + df.loc[fx_set, 'Asset_Class'] + '_' + df.loc[fx_set, 'FX_HS_CCY']

""" 8. Build Applied Buy/Sell and Applied Call/Put """
df['Applied_Call_Put'] = df.apply(lambda row: sl.SwitchFXOptionType(row['Asset_Type'], row['Switch_FX'], row['Product_Type'], row['Call_Put']), axis = 1)
df['Applied_Buy_Sell'] = df.apply(lambda row: sl.SwitchFXBuySell(row['Asset_Type'], row['Product_Type'], row['FX_HS_CCY'], row['CCY_Receive_Leg'], row['CCY_Pay_Leg'], row['Buy_Sell']), axis = 1)

""" 9. Delta """
# Pay Fixed (in fixed/float swap) -> Short position in interest rate curve
# Pay Float (in fixed/float swap) -> Long position in interest rate curve      
df['Delta'] = df.apply(lambda row: sl.SaccrDelta(row['Asset_Type'], row['Product_Type'], row['Underlying_Asset'],
                                                 row['Applied_Buy_Sell'], row['Applied_Call_Put'], 
                                                 row['Underlying_Price'], row['Underlying_Strike'],
                                                 row['T'], row['FX_HS_CCY'], row['Underlying_Quoted_CCY']), axis = 1)    


""" 10. Map supervisory parameters: SF, Correlation """
df['SF'] = df.apply(lambda row: sl.GetSF(row['Asset_Type'], 'BB', row['Underlying_Asset']), axis = 1)
df['Corr'] = df.apply(lambda row: sl.GetCorrelation(row['Asset_Type'], row['Underlying_Asset']), axis=1)

""" 11. Calc Add-On on position level """
df['Add_On_Position'] = df['Delta']*df['SF']*df['MF']*df['AdjustedNotional']


####################################################################################################
# PART 2: Aggregate -> Calc Addon -> dis aggregate to effective notional level -> calc SACCR
####################################################################################################
""" 12. Calc Effective Notional = sum_over_hs(Add_On_Position) """
# To secure that "group by" is working we can have no NaN only "NaN"
df['Underlying_Asset'] = df['Underlying_Asset'].fillna('NaN')
df.loc[ir_set, 'IR_Currency'] = df.loc[ir_set,'CCY_Receive_Leg']
df['IR_Currency'] = df['IR_Currency'].fillna('NaN')

# GroupBy multiple columns using pivot function
# i.   IR: aggregate over IR_Time_BUcket + IR_Currency
# ii.  FX: aggregate over Hedge_Set_Id
# iii. CR, EQ, CO: aggregate over Underlying_Asset
df_effective_notional = df.groupby(['Netting_Set', 'Hedge_Set_Id', 'Asset_Type', 'IR_Time_Bucket', 'IR_Currency', 'Underlying_Asset', 'Corr'], as_index =False)[['Market_Value', 'Collateral_Cover_Value', 'AdjustedNotional', 'Add_On_Position']].apply(sum)

""" 13. Add-On for Hedge set """
# FX: take abs() to arrive at Add_On_HS
fx_set_eff = (df_effective_notional['Asset_Type']==2)
df_fx_eff = df_effective_notional.loc[fx_set_eff]
num_fx_rows = len(df_fx_eff.index)
if num_fx_rows>0:
    df_fx_eff.loc[:,'Add_On_HS'] = df_fx_eff.loc[:,'Add_On_Position'].apply(abs)

# IR: aggregate over E_i's .... MAP back to df_effective_notional table!
df_ir_eff = df_effective_notional.loc[df_effective_notional.Asset_Type==1]
num_ir_rows = len(df_ir_eff.index)
if num_ir_rows>0:
    ir_dist = df_ir_eff.groupby(['Hedge_Set_Id'], as_index=False)[['Add_On_Position']].apply(sum)
    ir_dist.columns = ['Hedge_Set_Id', 'Tot_AN']
    df_ir_eff = pd.merge(df_ir_eff, ir_dist, on='Hedge_Set_Id', how='left')
    df_ir_eff['IR_Dist'] = df_ir_eff['Add_On_Position']/df_ir_eff['Tot_AN']

    # i. Number IR Hedge
    num_ir_hs = len(df_ir_eff['Hedge_Set_Id'].drop_duplicates())
    # ii. Unique list of Netting sets
    lst_ns = df_ir_eff['Netting_Set'].drop_duplicates() 
    # iii. Table for output of Add_on on Hedge Set level
    df_ir_hs = pd.DataFrame(index=range(num_ir_hs), columns=range(6))
    df_ir_hs.columns = ['Hedge_Set_Id', 'IR_Currency', 'Market_Value', 'Collateral_Cover_Value','AdjustedNotional', 'Add_On_HS']

    k = 0
    for i in range(0, len(lst_ns)):
        ns = lst_ns.iloc[i]
        lst_ccy = df_ir_eff.loc[df_ir_eff.Netting_Set==ns,'IR_Currency'].drop_duplicates()
        size_ccy_lst = len(lst_ccy)
            
        for j in range(0, size_ccy_lst):         
            ccy = lst_ccy.iloc[j]                 
            df_ir_hs.at[j + k, 'Netting_Set'] = ns
            df_ir_hs.at[j + k, 'Hedge_Set_Id'] = df_ir_eff.loc[(df_ir_eff.IR_Currency == ccy) & (df_ir_eff.Netting_Set == ns), ['Hedge_Set_Id', 'IR_Currency']].iloc[0,0]
            df_ir_hs.at[j + k, 'IR_Currency'] = df_ir_eff.loc[(df_ir_eff.IR_Currency == ccy) & (df_ir_eff.Netting_Set == ns), ['Hedge_Set_Id', 'IR_Currency']].iloc[0,1]
            df_ir_hs.at[j + k, 'Market_Value'] = np.nansum(df_ir_eff.loc[(df_ir_eff['Netting_Set'] == ns) & (df_ir_eff['IR_Currency'] == ccy), 'Market_Value'])
            df_ir_hs.at[j + k, 'Collateral_Cover_Value'] = np.nansum(df_ir_eff.loc[(df_ir_eff['Netting_Set'] == ns) & (df_ir_eff['IR_Currency'] == ccy), 'Collateral_Cover_Value'])
            df_ir_hs.at[j + k, 'AdjustedNotional'] = np.nansum(df_ir_eff.loc[(df_ir_eff['Netting_Set'] == ns) & (df_ir_eff['IR_Currency'] == ccy), 'AdjustedNotional'])        
            e1 = np.nansum(df_ir_eff.loc[(df_ir_eff['Netting_Set'] == ns) & (df_ir_eff['IR_Currency'] == ccy) & (df_ir_eff['IR_Time_Bucket'] == 'E1'), 'Add_On_Position'])
            e15 = np.nansum(df_ir_eff.loc[(df_ir_eff['Netting_Set'] == ns) & (df_ir_eff['IR_Currency'] == ccy) & (df_ir_eff['IR_Time_Bucket'] == 'E15'), 'Add_On_Position'])
            e5 = np.nansum(df_ir_eff.loc[(df_ir_eff['Netting_Set'] == ns) & (df_ir_eff['IR_Currency'] == ccy) & (df_ir_eff['IR_Time_Bucket'] == 'E5'), 'Add_On_Position'])             
            df_ir_hs.at[j + k, 'Add_On_HS'] = sl.IrEffectiveNotional(e1, e15, e5) 
        k += size_ccy_lst
        
        # Left join Add_On_HS back to df_ir_eff
    df_ir_eff = pd.merge(df_ir_eff, df_ir_hs[['Hedge_Set_Id', 'Add_On_HS']], on='Hedge_Set_Id', how='left')
        # Adjust for IR_Distribution (breakdown on CCY level)
    df_ir_eff['Add_On_HS'] = df_ir_eff['Add_On_HS']*df_ir_eff['IR_Dist']
    df_ir_eff = df_ir_eff.drop(['Tot_AN', 'IR_Dist'], axis=1)

# CO (HedgeSet) + CR, EQ (Asset Class):
co_cr_eq_set = (df_effective_notional['Asset_Type'] >= 3)
df_co_cr_eq_eff = df_effective_notional.loc[co_cr_eq_set]
num_co_cr_eq = len(df_co_cr_eq_eff.index)

if num_co_cr_eq>0:
    df_co_cr_eq_eff['Add_On_Corr'] = df_co_cr_eq_eff['Add_On_Position']*df_co_cr_eq_eff['Corr']
    df_co_cr_eq_eff['Add_On_1M_Corr'] = (1 - pow(df_co_cr_eq_eff['Corr'],2))*pow(df_co_cr_eq_eff['Add_On_Position'], 2)

    # Aggregate to effective notional level
    df_co_cr_eq_hs = df_co_cr_eq_eff.groupby(['Netting_Set', 'Hedge_Set_Id', 'Asset_Type'], as_index=False)[['Add_On_Corr', 'Add_On_1M_Corr']].apply(sum)

    # Calculate "correlation" for Commodity only
only_commodity = (df_co_cr_eq_hs['Asset_Type']==5)
df_co_hs = df_co_cr_eq_hs[only_commodity]
num_co = len(df_co_hs)
if num_co>0:
    df_co_hs['Add_On_HS'] = df_co_hs.apply(lambda row: sl.CalcAddOnAC(row['Add_On_Corr'], row['Add_On_1M_Corr']), axis=1)

    # Calculate for EQ + CR on Asset Class level
cr_eq_commodity = (df_co_cr_eq_hs['Asset_Type']<5)
df_cr_eq_hs = df_co_cr_eq_hs[cr_eq_commodity]
num_cr_eq = len(df_cr_eq_hs.index)
    # Aggregate over Asset Type 
    # 1. sum up to asset type
    # 2. apply "correlation-formula"
if num_cr_eq>0:
    lst = np.array(['Netting_Set', 'Asset_Type'])
    df_cr_eq_as = df_cr_eq_hs.groupby(['Netting_Set', 'Asset_Type'], as_index = False)[['Add_On_Corr', 'Add_On_1M_Corr']].apply(sum)
    df_cr_eq_as['Add_On_AS'] = df_cr_eq_as.apply(lambda row: sl.CalcAddOnAC(row['Add_On_Corr'], row['Add_On_1M_Corr']), axis=1)

    #Distribution commodity
commodity_eff = (df_co_cr_eq_eff['Asset_Type']==5)
df_co_eff = df_co_cr_eq_eff[commodity_eff]

num_co_eff = len(df_co_eff.index)
if num_co_eff>0:
    df_co_eff['Abs_Add_On_Pos'] = df_co_eff['Add_On_Position'].abs()
    df_co_eff_sum = df_co_eff.groupby(['Hedge_Set_Id'], as_index=False)[['Abs_Add_On_Pos']].apply(sum)
    df_co_eff_sum.columns = ['Hedge_Set_Id', 'Agg_Add_On']
    df_co_eff = pd.merge(df_co_eff, df_co_eff_sum, on='Hedge_Set_Id', how='left')
    df_co_eff['co_dist'] = df_co_eff['Abs_Add_On_Pos']/df_co_eff['Agg_Add_On']

    df_co_eff = pd.merge(df_co_eff, df_co_hs[['Hedge_Set_Id','Add_On_HS']], on='Hedge_Set_Id', how='left')
    df_co_eff['Add_On_HS'] = df_co_eff['Add_On_HS']*df_co_eff['co_dist']
    df_co_eff = df_co_eff.drop(['Add_On_Corr','Add_On_1M_Corr','Abs_Add_On_Pos', 'Agg_Add_On','co_dist'], axis=1)

    # Distribution EQ + CR
cr_eq_eff = (df_co_cr_eq_eff['Asset_Type']<5)
df_cr_eq_eff = df_co_cr_eq_eff[cr_eq_eff]
num_cr_eq_eff = len(df_cr_eq_eff.index)
if num_cr_eq_eff>0:
    df_cr_eq_eff['Abs_Add_On_Pos'] = df_cr_eq_eff[['Add_On_Position']].apply(abs)
    df_cr_eq_eff_sum = df_cr_eq_eff.groupby(['Asset_Type'], as_index=False)[['Abs_Add_On_Pos']].apply(sum)
    df_cr_eq_eff_sum.columns = ['Asset_Type', 'Agg_Add_On']
    df_cr_eq_eff = pd.merge(df_cr_eq_eff, df_cr_eq_eff_sum, on='Asset_Type', how='left')
    df_cr_eq_eff['asset_type_dist'] = df_cr_eq_eff['Abs_Add_On_Pos']/df_cr_eq_eff['Agg_Add_On']

    df_cr_eq_eff = pd.merge(df_cr_eq_eff, df_cr_eq_as[['Asset_Type','Add_On_AS']], on='Asset_Type', how='left')
    df_cr_eq_eff['Add_On_AS'] = df_cr_eq_eff['Add_On_AS']*df_cr_eq_eff['asset_type_dist']
    df_cr_eq_eff = df_cr_eq_eff.drop(['Add_On_Corr','Add_On_1M_Corr','Abs_Add_On_Pos', 'Agg_Add_On','asset_type_dist'], axis=1)
    df_cr_eq_eff.rename(columns={'Add_On_AS': 'Add_On_HS'}, inplace=True)


############################################################
#  *** RESULT on EFFECTIVE NOTIONAL LEVEL   ***
############################################################
df_result_eff = pd.concat([df_ir_eff, df_fx_eff])
df_result_eff = pd.concat([df_result_eff, df_co_eff], ignore_index=True)
df_result_eff = pd.concat([df_result_eff, df_cr_eq_eff], ignore_index=True)


############################################################
#  *** calc SACCR Numbers   ***
############################################################
df_total_saccr = df_result_eff.groupby(['Netting_Set'], as_index =False)[['Market_Value', 'Collateral_Cover_Value', 'Add_On_HS']].apply(sum)
df_total_saccr['Multiplier'] = df_total_saccr.apply(lambda row: sl.Multiplier(row['Market_Value'], row['Collateral_Cover_Value'], row['Add_On_HS']), axis=1)
df_total_saccr['Replacement_Costs'] = df_total_saccr.apply(lambda row: sl.ReplacementCosts(row['Market_Value'],row['Collateral_Cover_Value']), axis=1)
df_total_saccr['PFE'] = df_total_saccr.apply(lambda row: sl.PFE(row['Multiplier'],row['Add_On_HS']), axis=1)
df_total_saccr['SACCR_EAD'] = df_total_saccr.apply(lambda row: sl.EAD(row['Replacement_Costs'], row['PFE']), axis=1)


############################################################
#  *** Print Results + Export
############################################################

def main():
    print(df)
    print(df_result_eff)
    print(df_total_saccr)

if __name__ == "__main__":
    main()
 
file_df = 'saccr_pos.xlsx'
file_name1 = 'saccr_aggregated.xlsx'
file_name2 = 'saccr_eff_notional.xlsx'
#df.to_excel(file_location + file_df)
#df_result_eff.to_excel(file_location + file_name1)
#df_total_saccr.to_excel(file_location + file_name2)

