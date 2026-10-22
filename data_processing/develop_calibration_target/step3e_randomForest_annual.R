#Jeremy Giovando (jeremy.giovando@pnnl.gov)
#FORESIGHT - VIC Calibration Data Creation
#STEP 3e (final model training and prediction)
#This script uses the ANNUAL time series to train a RF model that will be used
#to predict the USGS flows in watersheds where only the GRFR is currently 
#available.
library(dplyr)
library(lubridate)
library(sf)
library(hydroGOF)
library(ggplot2)
library(vip)
library(ranger)
library(dataRetrieval)
mainPath="input_data/calibration_target/"
predict_new_basins=TRUE

#Check that output directory exists
dir_path=paste0(mainPath,"Data/output/summary/final models/annual/")
if (!dir.exists(dir_path)) {
  dir.create(dir_path, recursive = TRUE)
}

hucsToUse=c("01","04","09","10","13","15","17","18") #c("02",03","05","06","07","08","11","12","14","16")
for (h in hucsToUse){
  huc02_val=h
  ################################################################################
  #---Read in cluster files
  #NEED TO SPECIFY WHICH CLUSTER OUTPUT WE ARE USING FOR THE ANALYSIS
  centerVal=1
  cl.files=list.files(paste0(mainPath,"Data/output/summary/clusters/"),full.names = T,pattern = ".csv$")
  clusterFileToGet=cl.files[grepl(paste0(huc02_val,"_centers_",centerVal,".csv"),cl.files)]
  cl=read.csv(clusterFileToGet)
  #cl$HUC=as.character(zeroPad(cl$HUC,12))
  ################################################################################
  #---Read in the USGS quick flow file
  qf.files=list.files(paste0(mainPath,"Data/output/monthly/"),full.names = T,pattern = ".parquet$")
  qf.files_sub=qf.files[grep(paste0("USGS_HUC_",huc02_val),qf.files)]
  qf=read_parquet(qf.files_sub)
  qf$Date=as.POSIXct(qf$Date,"%Y-%m-%d",tz="GMT")
  qf$Dataset="USGS"
  qf$Year=year(qf$Date)
  qf$HUC=as.numeric(qf$HUC)
  ################################################################################
  #---Read in GRFR runoff csv file (spatial average values)
  gr.files=list.files(paste0(mainPath,"Data/output/monthly"),full.names = T,pattern = ".parquet$")
  gr.files_sub=gr.files[grep(paste0("GRFR_HUC_",huc02_val,"_monthly.parquet"),gr.files)]
  gr=read_parquet(gr.files_sub)
  gr=na.omit(gr)
  gr$Date=as.POSIXct(gr$Date,"%Y-%m-%d",tz="GMT")
  gr=gr[,names(gr) %in% c("HUC","runoff_month_sum","Date")]
  gr$Dataset="GRFR"
  gr$Year=year(gr$Date)
  gr$HUC=as.numeric(gr$HUC)
  ################################################################################
  #Get min/max dates that are common for both datasets
  minDate=max(min(qf$Date),min(gr$Date))
  maxDate=min(max(qf$Date),max(gr$Date))
  qf=qf[minDate <= qf$Date & qf$Date <= maxDate,]
  gr=gr[minDate <= gr$Date & gr$Date <= maxDate,]
  #Aggregate to annual total runoff
  qf_ann=qf %>%
          group_by(HUC,Year,Dataset) %>%
          summarise(runoff_ann_sum=sum(runoff_month_sum,na.rm = T))
  gr_ann=gr %>%
    group_by(HUC,Year,Dataset) %>%
    summarise(runoff_ann_sum=sum(runoff_month_sum,na.rm = T))
  #-----------------------------------------------
  #---MODEL DEVELOPMENT AND TRAINING
  #-----------------------------------------------
  for (c in 1:centerVal){
    #---Subset data files by HUC and cluster
    clusterNum=c
    #USGS watersheds filtered by cluster value
    qf_cl=left_join(qf_ann,cl,by="HUC")
    qf_cl_subset=na.omit(qf_cl[qf_cl$cluster_mean==clusterNum,])
    hucs_qf=unique(qf_cl_subset$HUC)
    #GRFR watersheds filtered by cluster value
    gr_cl <- left_join(gr_ann, cl, by = "HUC")
    gr_cl_subset <- gr_cl[gr_cl$cluster_mean == clusterNum & gr_cl$HUC %in% hucs_qf, ]
    gr_cl_predict=gr_cl[gr_cl$cluster_mean==clusterNum & !(gr_cl$HUC %in% hucs_qf),]
    hucs_gr=unique(gr_cl_subset$HUC)

    # --- FIX: Join on HUC and Year instead of cbind ---
    df_train <- inner_join(
      qf_cl_subset %>% select(HUC, Year, USGS_QF = runoff_ann_sum, clusterVal = cluster_mean),
      gr_cl_subset %>% select(HUC, Year, GRFR = runoff_ann_sum),
      by = c("HUC", "Year")
    )
    df_train$Year_val <- factor(df_train$Year)
    #Stats comparing USGS QF and GRFR data for specific HUC
    pearson_r=cor(df_train$USGS_QF,df_train$GRFR,method = 'pearson')^2
    nseVal=NSE(df_train$USGS_QF,df_train$GRFR)
    kgeVal=KGE(df_train$USGS_QF,df_train$GRFR)
    # Add years of lagged values to a data frame; determined from testing
    years_of_lag=2
    # Generate lagged columns using a loop
    df_train <- df_train %>%
      group_by(HUC)
    
    for (i in seq_len(years_of_lag)) {
      df_train <- df_train %>%
        mutate(!!paste0("GRFR_lag", i) := lag(GRFR, n = i))
    }
    df_train <- df_train %>% ungroup()  # Remove grouping
    
    #Filter data frame to only have complete rows of data (no NA's)
    filtered_df <- na.omit(df_train)
    
    #-----------------------------------------------
    #---RANDOM FOREST MODEL TRAINING
    #-----------------------------------------------
    # Dynamically create the formula
    lagged_columns <- paste0("GRFR_lag", 1:years_of_lag) 
    predictors <- c("GRFR", lagged_columns)   
    formula <- as.formula(paste("USGS_QF ~", paste(predictors, collapse = " +")))  # Create formula
    assign(paste0("laggedValue_formula"),formula) 
    
    set.seed(123)
    # Create indices for training (80%)
    train_indices <- caret::createDataPartition(filtered_df$USGS_QF, p = 0.80, list = FALSE)
    
    # Split the data
    train_data <- filtered_df[train_indices, ]  # Training data
    plot_1_1(train_data,pathToSave = paste0(mainPath,"Data/output/plots/annual/"),hucVal = huc02_val,clusterNum = clusterNum,centerVal)
    
    test_data <- filtered_df[-train_indices, ]  # Testing data
    
    rf.model_lag <- ranger::ranger(laggedValue_formula,
                                   data = train_data,
                                   num.tree = 100,
                                   importance = 'permutation')
    predictions_lag=predict(rf.model_lag,test_data)
    
    # Get the final OOB error rate (the last value in the first column)
    oob_error_lag <- rf.model_lag$prediction.error
    oob_rmse_lag <- sqrt(oob_error_lag)
    oob_r2_lag <- rf.model_lag$r.squared
    rmse_lag=rmse(predictions_lag$predictions,test_data$USGS_QF)
    r2_lag=cor(predictions_lag$predictions,test_data$USGS_QF,method = 'pearson')^2
    
    # View the variable importance scores
    importance(rf.model_lag)
    
    # Plot the variable importance
    vip_plot <- vip(rf.model_lag)
    
    # Customize the plot
    vip_plot <- vip_plot +
      labs(
        title = paste0("Variable Importance Plot for RF Model\n(HUC:",huc02_val," Cluster ",clusterNum,")"), 
        x = "Inputs",        
        y = "Importance Score"
      ) +
      theme_minimal() # Optional: improves overall aesthetics
    
    # Print the customized plot
    print(vip_plot)
    
    #Create prediction time series for all training watersheds
    predictions_lag_allWatersheds=predict(rf.model_lag,filtered_df)
    out_ts=data.frame(HUC=filtered_df$HUC,cluster=clusterNum,Year=filtered_df$Year_val,
                      USGS_obs=filtered_df$USGS_QF,USGS_pred=predictions_lag_allWatersheds$predictions,GRFR=filtered_df$GRFR)
    
    # Save the plot and summary file for model metrics and time series
    ggsave(paste0(mainPath,"Data/output/plots/annual/HUC_",huc02_val,"_cluster",clusterNum,"_",centerVal,".png"), vip_plot, width = 8, height = 6)
    out_df=data.frame(HUC02=huc02_val,cluster=clusterNum,R2_all=pearson_r,NSE_all=nseVal,KGE_all=kgeVal,
                      train_rmse=oob_rmse_lag,train_r2=oob_r2_lag,
                      test_rmse=rmse_lag, test_r2=r2_lag)
    fileName_metrics=paste0(mainPath,"Data/output/summary/final models/annual/model_metrics_RF_HUC_",huc02_val,"_",centerVal,".csv")
    fileName_ts=paste0(mainPath,"Data/output/summary/final models/annual/model_timeseries_RF_HUC_",huc02_val,"_",centerVal,".csv")
    if(!file.exists(fileName_metrics)){
      write.table(out_df,file=fileName_metrics,append=T, row.names = F, col.names=T, sep = ",")
      write.table(out_ts,file=fileName_ts,append=T, row.names = F, col.names=T, sep = ",")
    }else{
      write.table(out_df,file=fileName_metrics,append=T, row.names = F, col.names=F, sep = ",")
      write.table(out_ts,file=fileName_ts,append=T, row.names = F, col.names=F, sep = ",")
    }
    
    #---------------------------------------------------
    #---RANDOM FOREST MODEL PREDICTION (NEW WATERSHEDS)
    #---------------------------------------------------
    if(predict_new_basins){
      df_predict=data.frame(HUC=as.character(gr_cl_predict$HUC),Year=gr_cl_predict$Year,Year_val=factor(gr_cl_predict$Year),
                            GRFR=gr_cl_predict$runoff_ann_sum,clusterVal=gr_cl_predict$cluster_mean)
      
      df_predict <- df_predict %>%
        group_by(HUC)
      
      for (i in seq_len(years_of_lag)) {
        df_predict <- df_predict %>%
          mutate(!!paste0("GRFR_lag", i) := lag(GRFR, n = i))
      }
      df_predict <- df_predict %>% ungroup()
      #Filter data frame to only have complete rows of data (no NA's)
      filtered_df_predict <- na.omit(df_predict)
      
      #Create USGS QF predictions & observations
      filtered_df_predict$predictions_USGS <- predict(rf.model_lag, filtered_df_predict)$predictions
      
      #Filter to keep only needed results
      final_prediction_df=filtered_df_predict[,names(filtered_df_predict) %in% c("HUC","Year","clusterVal","GRFR","predictions_USGS")]
      filename_pred=paste0(mainPath,"Data/output/summary/final models/annual/predicted_USGS_HUC",huc02_val,"_",centerVal,".csv")
      if(!file.exists(filename_pred)){
        write.table(final_prediction_df, 
                  file = paste0(filename_pred), 
                  col.names=T, row.names = FALSE,sep = ",")
      }else{
        write.table(final_prediction_df, 
                    file = paste0(filename_pred), 
                    col.names=F,row.names = FALSE,sep = ",",append = T)
      }
    }
    
  } #End of loop over all clusters
}