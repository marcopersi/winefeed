package ch.persi.vino.gui2.client.marketdata.gui;

import com.smartgwt.client.data.Record;

public class ChartData extends Record {
	public ChartData(String theDate, String theWine, Integer thePrice) {  
        setAttribute("Datum", theDate);  
        setAttribute("Wein", theWine);  
        setAttribute("Preis", thePrice);  
    }  
  
    public static ChartData[] getData() {  
        return new ChartData[] {  
            new ChartData("01.01.2008", "Masseto", 550),  
            new ChartData("01.01.2009", "Masseto", 620),  
            new ChartData("01.01.2010", "Masseto", 680),  
            new ChartData("01.01.2011", "Masseto", 505),  
  
            new ChartData("01.01.2008", "Petrus", 1950),  
            new ChartData("01.01.2009", "Petrus", 2350),  
            new ChartData("01.01.2010", "Petrus", 3300),  
            new ChartData("01.01.2011", "Petrus", 4200),  
        };  
    }  
  
}
