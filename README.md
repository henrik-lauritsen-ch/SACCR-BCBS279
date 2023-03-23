# SACCR - [BCBS279](https://github.com/henrik-lauritsen-ch/SACCR-BCBS279/blob/main/bcbs279.pdf)

![alt text](https://github.com/henrik-lauritsen-ch/Pictures/blob/main/bcbs279_title.png)

![alt text](https://github.com/henrik-lauritsen-ch/Pictures/blob/main/bis_logo.png)

The SACCR repositry contains two python files that together calculated the counterparty exposure values for a derivatives portfolio of a financial institution. The calculation is run from the [Python Engine](https://github.com/henrik-lauritsen-ch/SACCR-BCBS279/blob/main/saccr_engine.py). Main engine imports the [SACCR Library](https://github.com/henrik-lauritsen-ch/SACCR-BCBS279/blob/main/saccr_engine.py) where general parameters of the method along with delta calculation and special functionality that is needed to deal with the so called Hedge set construction for FX derivatives (see below) is defined.


![alt text](https://github.com/henrik-lauritsen-ch/Pictures/blob/main/whitespace2.png)
## The Method: Calculation of Exposures, Assert Classes and Hedge Sets

### General formula for exposure calculation
The general formula for calculating the EAD of a Netting set is the sum of the **Replacements Costs (RC)** under a Netting set plus the **Potential Future Exposure (PFE)** multiplied by **alpha**:

 ![EAD](https://github.com/henrik-lauritsen-ch/Pictures/blob/main/bcbs279_generalformula.png)

where alpha is a constant set to 1.4.

- Replacements Costs are net market value of derivatives under a Netting set across all asset classes subtracted the collateral value allocated to the Netting set. RC are floored at zero.

![PFE](https://github.com/henrik-lauritsen-ch/Pictures/blob/main/bcbs279_RC.png)

where __V__ is net market value under Netting set and __C__ the allocated collateral value

- PFE is the potential future exposure of the market value under the RC. PFE is calculated to capture possible future changes in market values due to market movements. PFE is the sum over the Add-On value over the five asset classes multiplied with a so called Multiplier. The purpose of the latter is to take collateral values into account. i.e. the more collateral posted the lower the PFE value:

 ![PFE](https://github.com/henrik-lauritsen-ch/Pictures/blob/main/bcbs279_PFE.png)

with

 ![Multilpier](https://github.com/henrik-lauritsen-ch/Pictures/blob/main/bcbs279_multiplier.png)

and where __Floor__ a constant set to 5%.
  
  
  
### Asset Classes
Under the SACCR method five asset classes have been defined: Interest rate, Foreign Exchange, Credit, Equity and Commodity. Each of the five asset classes have a specific method for calculating the Add-On value. The Add-on values are positive (hence, no Netting between asset classes for the PFE calculation):

![Add-On](https://github.com/henrik-lauritsen-ch/Pictures/blob/main/bcbs279_addonagg.png)



### Hedge Sets
Under each of the five asset classes a more granular level called the Hedge set is defined. Within a Hedge set there is in general full Netting between short and long position. For commodities this is not quite the case. Please see [BSBC279](https://github.com/henrik-lauritsen-ch/SACCR-BCBS279/blob/main/bcbs279.pdf) for details on how to construct Hedge set. 

Building the Hedge set are more or less straight forward except for derivatives under the Foreign Exchange (FX) asset class where the following should be take into consideration:

- Each currency pair defines a unique Hedge set. I.e. the currency pairs EURUSD, USDAUD, EURNOK, ... etc are all Hedge sets.
- The order of the currencies of a currency pair is irrelevant seen from a Hedge set point of view. The means that e.g. all EURUSD and USDEUR positions under a Netting set form a unique Hedge set. Here it is importen decide to either see all positions as EURUSD or as USDEUR. This tool constructs the FX Hedge sets based on currencies in alphabetic order, i.e. all FX positions involving EUR and USD are considered EURUSD.
  
  1. Select unique currency pair, e.g. EURUSD, for your Hedge set

  2. Find delta of the linear products. For the buy EUR, sell USD this is seen from a EURUSD point of view a "buy" i.e. delta would be 1.0. The Buy USD, Sell EUR is considered a "sell" seen from a EURUSD point of view, which means that the delta should be -1.0
  3. In case there are FX option under a Netting set switching the cross around from USDEUR to EURUSD would not be done through the buy/sell sign but re-defining a call to a put (and the other way around) 


![alt text](https://github.com/henrik-lauritsen-ch/Pictures/blob/main/whitespace2.png)
## Import of financial data into the engine
The code assumes a certain structure of the input data in order to work. Also attribute names are hard coded. The [CSV-File](https://github.com/henrik-lauritsen-ch/SACCR-BCBS279/blob/main/base_data_saccr.csv) contains a small derivatives portfolio that can be applied for testing purposes. The names in the cvs-file are expected for the code to work. Further, we have provided a file containing data that calculates example 1 and 3 as shown in [bcbs279, Annex 4a](https://github.com/henrik-lauritsen-ch/SACCR-BCBS279/blob/main/test2_data.csv).


![alt text](https://github.com/henrik-lauritsen-ch/Pictures/blob/main/whitespace2.png)
## What was not implemented?
Following cases have not been taken into account:
- CDO tranches 
- Calculation of Replacements Costs for Margined Accounts
- Special cases of derivatives that require specific implementation
- Netting set consisting of only __short__ positions 
 
 Also, note that all notional values and prices are assumed to be in the same currency (CHF)
