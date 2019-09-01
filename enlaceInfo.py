import pandas as pd
import numpy as np

#Models
from sklearn.linear_model import  LassoLarsIC
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score
from sklearn.ensemble import RandomForestRegressor
from math import ceil

#Map
import folium 
from folium import plugins
from folium.plugins import MarkerCluster

class RiskScore:
    # En algún momento moverlo a una clase e importar la clase
    def normalize(self,dataset):   
        dataNorm=((dataset-dataset.min())/(dataset.max()-dataset.min()))
        return dataNorm 
    
 
    def format_data(self,df):
        df_N = self.normalize(df)
        df_small = self.make_small(df_N)
        df_small.drop(df_small.columns[df_small.isnull().sum()>0].tolist(), inplace=True, axis =1)
        return df_small
    

    def make_small(self,df):
        if 'Unnamed: 0' in df.columns:
            df.drop(['Unnamed: 0'], axis = 1, inplace=True)

        df[df.select_dtypes(include = ['float64']).columns] = df.select_dtypes(include = ['float64']).astype(np.float16)
        df[df.select_dtypes(include = ['int64']).columns] = df.select_dtypes(include = ['int64']).astype(np.int16)
        return df
    
  
    def r2a_score(self, y_test, y_pred, numPar, numObs):
        R2 = r2_score(y_test, y_pred)
        p = numPar
        n = numObs #test or train?
        adj = 1-(1-R2)*(n-1)/(n-p-1)
        return adj


    def get_risk_score_criteria(self, df_coefs, df_perc):
        varlist = df_coefs.index.tolist()
        df_rs = pd.DataFrame("", index=np.arange(0,len(varlist)*4).tolist(),columns=['Variable', 'Puntos', 'Condicion'])

        cont = 0
        for var in varlist:
            df_rs['Variable'][cont] = var

            if str(df_perc[0.5][var]) == "0.0":
                df_rs['Puntos'][cont]= df_coefs["Multiplicador"][var]*1
                df_rs['Condicion'][cont]= "Igual a cero"
                cont +=1  
                df_rs['Puntos'][cont]= df_coefs["Multiplicador"][var]*4
                df_rs['Condicion'][cont]= "Mayor a cero"
                cont +=1 
            else: 
                for i in range(1,5):
                    df_rs['Puntos'][cont]= df_coefs["Multiplicador"][var]*i

                    if i ==1:
                        resp = "Menor a " + str(df_perc[0.25][var])
                    if i == 2:
                        resp = "Mayor o igual a " + str(df_perc[0.25][var]) + " y menor que " + str(df_perc[0.5][var])
                    if i == 3: 
                        resp = "Mayor o igual a " + str(df_perc[0.5][var]) + " y menor que " + str(df_perc[0.75][var])
                    if i == 4:
                        resp =  "Mayor a " + str(df_perc[0.75][var])
                    df_rs['Condicion'][cont]= resp
                    cont +=1

        df_rs = df_rs[df_rs['Puntos']!=""]
        return df_rs


    def get_risk_score(self, df, reg):
        #Divide in test and train
        X = df.drop(['p_mat_std', 'cct'], axis=1)
        y = df[['p_mat_std']].astype('float32')
        labels = df[['cct']]
        Xn = self.format_data(X)
        X_train, X_test, y_train, y_test = train_test_split(Xn, y, 
                                                        test_size=0.2, 
                                                        random_state=15)
        #Sort variable importance: Use Random Forest
        reg_rf = RandomForestRegressor(n_jobs = -1, random_state = 10, oob_score = True, n_estimators = 100) 
        reg_rf.fit(X_train, y_train)
        feature_importances = pd.DataFrame(reg_rf.feature_importances_, index = X_train.columns,
                                          columns=['importance']).sort_values('importance',ascending=False)
        imp_feat = list(feature_importances.index)


        #Get the REAL important variables
        #Create models with 1 to n variables
        X_train_temp = X_train
        X_test_temp = X_test

        r2a_score_list = []
        tam = len(imp_feat)
        numObs = len(X_train)
        for i in range(1,tam+1):
            used_feat = imp_feat[:i]

            X_train = X_train_temp[used_feat]
            X_test = X_test_temp[used_feat]

            reg.fit(X_train.astype('float32'), y_train)
            y_pred = reg.predict(X_test)
            r2a = self.r2a_score(y_test, y_pred, i, numObs)
            r2a_score_list.append(r2a)

        #Select variables before growth rate gets very small
        numVars = pd.DataFrame(r2a_score_list).pct_change()>0.001
        i = len(numVars) -1
        while (i > 0) & (numVars[0][i]==False):
            i -= 1

        goodVars = imp_feat[:i]

        X_train = X_train_temp[goodVars]
        X_test = X_test_temp[goodVars]

        # Get model r2 score
        reg.fit(X_train.astype('float32'), y_train)
        y_pred = reg.predict(X_test)
        r2a_model = self.r2a_score(y_test, y_pred, len(goodVars), numObs)


        #Get the coefficient of the important variables
        if reg.coef_[0].size  == 1:
             coef = pd.Series(reg.coef_, index = X_train.columns)
        else:
            coef = pd.Series(reg.coef_[0], index = X_train.columns)
        imp_coef = coef.sort_values()

        #Gets multipliers values
        goodVars = imp_coef[abs(imp_coef.round(1)*10)>0.5].index.tolist()
        imp_coef = imp_coef[goodVars]
        df_round= pd.DataFrame(imp_coef.round(1)*10).sort_values(by=0)*(-1)
        df_coefs = pd.DataFrame(imp_coef).merge(df_round, right_index = True, left_index = True)
        df_coefs = df_coefs.rename({'0_x':'Original','0_y':'Multiplicador'}, axis = 1)

        #Gets percentiles limits per variables
        df_rs = df[goodVars]
        rs1 = pd.DataFrame(df_rs.quantile(0.25))
        rs2 = pd.DataFrame(df_rs.quantile(0.5))
        rs3 = pd.DataFrame(df_rs.quantile(0.75))
        df_perc = rs1.merge(rs2, right_index = True, left_index = True).merge(rs3, right_index = True, left_index = True).round(1)

        #Calculates bin values
        finalVars = goodVars + ['cct']
        df_rs = df[finalVars]
        var_list = goodVars
        for var in var_list:
            new_var = "rs_" + var
            df_rs[new_var] = 0
            df_rs.loc[df_rs[var] > df_perc[0.25][var], new_var] = 1
            df_rs.loc[df_rs[var] > df_perc[0.5][var], new_var] = 2
            df_rs.loc[df_rs[var] > df_perc[0.75][var], new_var] = 3

            df_rs[new_var] = df_rs[new_var] *df_coefs['Multiplicador'][var] 

        #Calculates risk score
        filter_col = [col for col in df_rs if col.startswith('rs')]
        filter_col_cct = filter_col + ['cct']
        df_rs_perc = df_rs[filter_col_cct]

        df_rs_perc['Total']= df_rs_perc.sum(axis=1)
        df_risk = df_rs_perc[['Total', 'cct']].sort_values(by='Total', ascending =False)

        #gets risk score criteria
        df_criteria = self.get_risk_score_criteria(df_coefs, df_perc)

        dicc_results = {}
        dicc_results["r2a"] = r2a_model
        dicc_results["coefs"] = df_coefs
        dicc_results["perc"] = df_perc
        dicc_results["risk"] = df_risk
        dicc_results["criteria"] = df_criteria
        return dicc_results
 
    def get_state_type(self, lista_estados, tipo):
        if tipo == "G" or tipo == "Pri" or tipo == "Pub" :
            df = pd.read_csv('data/general_clear.csv')
        if tipo == "I":
            df = pd.read_csv('data/indigena_clear.csv')
        if tipo == "C":
            df =  pd.read_csv('data/comunitaria_clear.csv')
        if tipo == "Pri":
            df = df[df["control"]==2]
        if tipo == "Pub":
            df = df[df["control"]==1]
        
        if len(lista_estados)>0 and lista_estados[0]>0:
            df["edo"] = df.cct.str[:2].astype("int")
            df = df[df['edo'].isin(lista_estados)]
            df = df.drop(["edo"], axis = 1)

        return df
 
    def get_all_info_filtered(self, estados, tipo, reg):
        df = self.get_state_type(estados, tipo)
        dicc_results = self.get_risk_score(df, reg)
        return dicc_results
    
    def get_map(self, df_risk,name):
        df_lat = pd.read_csv('data/escuelas_latlon.csv', encoding = 'latin-1')
        
        df =  pd.merge(df_risk, df_lat, on='cct' )
        
        cen_lon = df.longitud.mean()
        cen_lat = df.latitud.mean()

        mapi = folium.Map(location=[cen_lat,cen_lon],
                            zoom_start = 6,
                        tiles="cartodbpositron")

        df = df[:100]
        for col in range(len(df)):
            lon = df["longitud"][col]
            lat = df['latitud'][col]
            nombre = df["cct"][col]
            valor = df['Total'][col]
            tam = abs(valor)
            if valor > 0:
                color_sch = 'red'
                fill_sch = 'orange'
            else:
                color_sch = 'green'
                fill_sch = 'yellow'

            folium.features.CircleMarker(
            location=[lat,lon],
            radius=tam*100,
            popup=nombre,
            color=color_sch,
            fill_color = fill_sch,
            fill_opacity=0.2
            ).add_to(mapi)

        mapi.save(name)
       # return mapi