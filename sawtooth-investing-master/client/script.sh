#!/bin/bash


python3 invest.py addstartup JPMorgan www.jpmorganchase.comn israel 150000
python3 invest.py addstartup Fabric www.fabric.com israel 150000
python3 invest.py addstartup Flytrex www.flytrex.com usa 200000
python3 invest.py addstartup Gett www.gett.com israel 630000
python3 invest.py addstartup IronSource www.ironsource.com israel 200000
python3 invest.py addstartup Fivver www.fivver.com israel 200000
python3 invest.py addstartup Ponaryas www.ponaryas.com france 200000


python3 invest.py liststartups
python3 invest.py liststartups bylocation israel

python3 invest.py invest shlomi JPMorgan 50001
python3 invest.py invest afnan JPMorgan 50002
python3 invest.py invest amanda Gett 20000
python3 invest.py invest hussien JPMorgan 60000 


python3 invest.py liststartups
python3 invest.py liststartups bylocation israel
python3 invest.py listinvestors
python3 invest.py listinvestors bystartup JPMorgan


