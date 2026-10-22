#Jeremy Giovando (jeremy.giovando@pnnl.gov)
#FORESIGHT
#FUNCTIONS USED IN DEVELOPMENT OF VIC CALIBRATION DATA
##############################################################################

library(caret)
library(tidyverse)
library(forecast)
library(dplyr)
library(mgcv)
library(ggplot2)
#---MODELS----------------------------------------------------------------------
  time_series_linear_model <- function(
    data,                    # Input dataframe
    target_variable,         # Name of the target variable
    predictor_variables,     # Vector of predictor variable names
    k_folds,                 # Number of folds for cross-validation
    time_column = 'Date',    # Name of the time column
    seed = 123               # Random seed for reproducibility
  ) {
    # target_variable="USGS_QF"
    # predictor_variables="GRFR"
    # time_column='Date'
    # seasonal_column="Month_val"
    # data=df_train
    
    # Set random seed for reproducibility
    set.seed(seed)
    
    # Prepare the data
    model_data <- data %>%
      select(all_of(c(time_column, seasonal_column, target_variable, predictor_variables))) %>%
      na.omit()

    # Create time series index
    model_data <- model_data %>%
      #arrange(!!sym(time_column)) %>%
      mutate(time_index = row_number(),
             month_val=Month_val)

    # Prepare cross-validation
    # control <- trainControl(
    #   method = "timeslice",
    #   horizon= 1,
    #   initialWindow = 1000,
    #   fixedWindow = T,
    #   #number = k_folds,
    #   verboseIter = TRUE,
    #   allowParallel = TRUE,
    #   # Parallel backend
    #   returnResamp = "all"
    # )
    control <- trainControl(
      method = "cv",
      number = k_folds,
      verboseIter = TRUE,
      allowParallel = TRUE,
      # Parallel backend
      returnResamp = "all"
    )
    # Train the model with time series cross-validation
    model_formula=as.formula(paste(target_variable, " ~ ",predictor_variables,"+ time_index + month_val"))
    model <- train(model_formula,
                    data=model_data,
                    preProcess = c('center','scale'),
                    method = "lm",
                    trControl = control,
                    metric = "RMSE"
                )
    return(model)
  }
########################################################  
  time_series_nonlinear_model <- function(
    data,                    # Input dataframe
    target_variable,         # Name of the target variable
    predictor_variables,     # Vector of predictor variable names
    k_folds,                 # Number of folds for cross-validation
    seasonal_column,           # Name of the time column
    seed = 123               # Random seed for reproducibility
  ) {
    target_variable="USGS_QF"
    predictor_variables="GRFR"
    time_column='Date'
    seasonal_column="Month_val"
    data=df_train
    
    # Set random seed for reproducibility
    set.seed(seed)
    
    # Prepare the data
    model_data <- data %>%
      select(all_of(c(seasonal_column, target_variable, predictor_variables))) %>%
      na.omit()

    control <- trainControl(
      method = "cv",
      number = 5,
      verboseIter = TRUE
    )
    # Train the model with time series cross-validation
    model_formula=as.formula(paste(target_variable, " ~ ",predictor_variables))
    model <- train(model_formula,
                   data=model_data,
                   preProcess = c('center','scale'),
                   method = "bam",
                   trControl = control,
                   metric = "RMSE"
    )
    return(model)
  }
################################
  time_series_pls_model <- function(
    data,                    # Input dataframe
    target_variable,         # Name of the target variable
    predictor_variables,     # Vector of predictor variable names
    k_folds,                 # Number of folds for cross-validation
    # seasonal_column,           # Name of the time column
    seed = 123               # Random seed for reproducibility
  ) {
    library(caret)
    library(doParallel)
    
    # Register the parallel backend
    # Detect the number of available cores
    cores <- detectCores()-8
    
    # Create a cluster with the number of detected cores
    cl <- makeCluster(cores)
    
    # Register the cluster as the parallel backend for foreach
    registerDoParallel(cl)
    
    # Set random seed for reproducibility
    set.seed(seed)
    
    # Prepare the data
    model_data <- data %>%
      select(all_of(c(target_variable, predictor_variables))) %>%
      na.omit()
 
    control <- trainControl(
      method = "cv",
      number = 5,
      verboseIter = TRUE,
      allowParallel = T
    )
    # Train the model with time series cross-validation
    model_formula=as.formula(paste(target_variable, " ~ ",predictor_variables))
    model <- train(model_formula,
                   data=model_data,
                   preProcess = c('center','scale'),
                   method = "pls",
                   trControl = control,
                   metric = "RMSE"
    )
    
    #Stop the parallel backend
    stopCluster(cl)
    # Revert to sequential processing
    registerDoSEQ()
    
    return(model)
  }
#####################################
  time_series_qrnn_model <- function(
    data,                    # Input dataframe
    target_variable,         # Name of the target variable
    predictor_variables,     # Vector of predictor variable names
    k_folds,                 # Number of folds for cross-validation
    seasonal_column,           # Name of the time column
    seed = 123               # Random seed for reproducibility
  ) {
    library(qrnn)
    library(caret)
    library(doParallel)
    
    # Register the parallel backend
    # Detect the number of available cores
    cores <- detectCores()-8
    
    # Create a cluster with the number of detected cores
    cl <- makeCluster(cores)
    
    # Register the cluster as the parallel backend for foreach
    registerDoParallel(cl)
    # Set random seed for reproducibility
    set.seed(seed)
    
    # Prepare the data
    model_data <- data %>%
      select(all_of(c(seasonal_column, target_variable, predictor_variables))) %>%
      na.omit()
    
    control <- trainControl(
      method = "cv",
      number = 5,
      verboseIter = TRUE,
      allowParallel = T
    )
    # Train the model with time series cross-validation
    model_formula=as.formula(paste(target_variable, " ~ ",predictor_variables,"+ Month_val"))
    model <- train(model_formula,
                   data=model_data,
                   preProcess = c('center','scale'),
                   method = "qrnn",
                   trControl = control,
                   metric = "RMSE"
    )
    
    #Stop the parallel backend
    stopCluster(cl)
    # Revert to sequential processing
    registerDoSEQ()
    
    return(model)
  }
#########################################
time_series_nn_model <- function(
  data,                    # Input dataframe
  target_variable,         # Name of the target variable
  predictor_variables,     # Vector of predictor variable names
  k_folds,                 # Number of folds for cross-validation
  seasonal_column,           # Name of the time column
  seed = 123               # Random seed for reproducibility
) {
  #library(nnet)
  library(brnn)
  library(caret)
  library(doParallel)
  
  # Register the parallel backend
  # Detect the number of available cores
  cores <- detectCores()-8
  
  # Create a cluster with the number of detected cores
  cl <- makeCluster(cores)
  
  # Register the cluster as the parallel backend for foreach
  registerDoParallel(cl)
  # Set random seed for reproducibility
  set.seed(seed)
  
  # Prepare the data
  model_data <- data %>%
    select(all_of(c(seasonal_column, target_variable, predictor_variables))) %>%
    na.omit()
  
  control <- trainControl(
    method = "cv",
    number = 5,
    verboseIter = TRUE,
    allowParallel = T
  )
  # Train the model with time series cross-validation
  model_formula=as.formula(paste(target_variable, " ~ ",predictor_variables,"+ Month_val"))
  model <- train(model_formula,
                 data=model_data,
                 preProcess = c('center','scale'),
                 method = "brnn",
                 trControl = control,
                 metric = "RMSE"
  )
  
  #Stop the parallel backend
  stopCluster(cl)
  # Revert to sequential processing
  registerDoSEQ()
  
  return(model)
}
#---MODEL PERFORMANCE-----------------------------------------------------------
# Model performance metrics
performance_metrics <- function(modelObject) {
  # Predictions
  predictions <- modelObject$finalModel$fitted.values
  obs <- modelObject$trainingData$.outcome
  # Calculate performance metrics
  rmse <- sqrt(mean((predictions - obs)^2))
  mae <- mean(abs(predictions - obs))
  r_squared <- cor(predictions, obs)^2
  
  return(list(
    RMSE = rmse,
    MAE = mae,
    R_Squared = r_squared,
    Performance_Summary = summary(model)
  ))
}

# Residual analysis function
residual_analysis <- function(modelObject) {
  library(nortest)
  # Final model
  final_model <- modelObject$finalModel
  
  # Residual plot
  residuals_plot <- ggplot() +
    geom_point(aes(x = fitted(final_model), 
                   y = residuals(final_model))) +
    geom_hline(yintercept = 0, linetype = "dashed", color = "red") +
    labs(title = "Residuals vs Fitted",
         x = "Fitted Values", 
         y = "Residuals")
  
  # Normality of residuals
  ad_test <- ad.test(residuals(final_model))
  
  return(list(
    Residuals_Plot = residuals_plot,
    AndersonDarling_Test = ad_test
  ))
}
#---PLOTTING-------------------------------------------------------------------
comparison_plot <- function(modelObject){
  predictions <- modelObject$finalModel$fitted.values
  obs <- modelObject$trainingData$.outcome
  
  ggplot() +
  geom_point(aes(x = obs, y = predictions)) +
  geom_abline(intercept=0,linetype = "dashed", color = "red") +
  labs(title = "Predicted vs Observed",
       x = "Observed Values", 
       y = "Predicted Values")
}

timeseries_plot <- function(modelObject){
  predictions <- modelObject$finalModel$fitted.values
  obs <- modelObject$trainingData$.outcome
  time <- modelObject$trainingData$time_index
  ggplot() +
    geom_line(aes(x = time, y = predictions),linetype = "dashed",color = "red") +
    geom_line(aes(x=time, y=obs),color = "grey",alpha=0.5) +
    labs(title = "Predicted vs Observed",
         x = "Time", 
         y = "Runoff Values")
}

plot_1_1 <- function(data_frame,pathToSave,hucVal,clusterNum,totalClusterVal){
  # Step 1: Standardize GRFR and USGS_QF values in the test_data dataframe
  temp_df <- data_frame %>%
    mutate(
      GRFR_standardized = (GRFR - mean(GRFR, na.rm = TRUE)) / sd(GRFR, na.rm = TRUE),
      USGS_QF_standardized = (USGS_QF - mean(USGS_QF, na.rm = TRUE)) / sd(USGS_QF, na.rm = TRUE)
    )
  
  # Step 2: Create a 1:1 scatterplot
  ggplot(temp_df, aes(x = GRFR_standardized, y = USGS_QF_standardized)) +
    geom_point(color = "blue", alpha = 0.6) +  # Add points
    geom_abline(intercept = 0, slope = 1, color = "red", linetype = "dashed") +  # 1:1 line
    labs(
      title = paste0("Standardized GRFR vs Standardized USGS QF Values\nHUC:",
                     hucVal," Cluster",clusterNum),      
      x = "Standardized GRFR Values",                                           # X-axis label
      y = "Standardized USGS QF Values"                                         # Y-axis label
    ) +
    theme_minimal()  # Clean theme for aesthetics
  
  # Step 3: Save the plot to a file
  ggsave(paste0(pathToSave,"standardized_1to1_",hucVal,"_",clusterNum,"_",totalClusterVal,"plot.png"), width = 8, height = 6)
}