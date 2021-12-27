# sawtooth-investing
A hyperledger sawtooth application for investing  
The application uses blockchain and docker containers to store the startups, investors and budget count.  

## Instructions for use
Build the necessary components used by the application using docker-compose.yaml file by running:  
  `[sudo] docker-compose up`  
  Run the client.py file as shown below, inside the container investing-client :  
  `docker exec -it investing-client bash`  
  Now we are inside the client docker
  .
## Use cases and commands
 #### 1. Add start-Up
 Start-Ups are identified by their names. Start-Ups can be added exactly once.  
  `python3 invest.py addstartup StartupName Url Location Amount`
 #### 2. invest in 
 persons can invest for more than one startup; investors are identified by their names.  
  
  `python3 invest.py invest InvestorName StartupsName Amount`  

 #### 3. List Start-Ups and Investors
 List all added Start-Ups and Investors who have invested.  
 `python3 invest.py liststartups`
 `python3 invest.py liststartups bylocation Location`  
 `python3 invest.py listinvestors`  
 
