package ch.persi.java.vino.importers.wermuth;

import groovy.lang.GroovyClassLoader;
import groovy.lang.GroovyObject;
import groovy.util.ResourceException;
import groovy.util.ScriptException;

import java.io.File;
import java.io.IOException;
import java.math.BigDecimal;
import java.net.URL;
import java.net.URLConnection;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import org.joda.time.DateTime;

import ch.persi.java.vino.dao.IDao;
import ch.persi.java.vino.domain.Offering;
import ch.persi.java.vino.importers.Task;
import ch.persi.java.vino.util.SpringUtil;

public class WermuthUpdatePriceTask implements Task {

	private static final String WERMUTH_BASE_HTTP_URL = "http://www.wermuth.ch/ErgebnisseWZ";
	final IDao dao;
	final String realizedPriceUrl;
    DateTime auctionDate; 
    private static final Pattern anAuctionPattern = java.util.regex.Pattern.compile(".*Weinauktion_WZ_([0-9]{3}).*");

    public WermuthUpdatePriceTask(String theFileName, DateTime theAuctionDate)
    {
    	dao = (IDao) SpringUtil.getContext().getBean("dao"); 
    	auctionDate = theAuctionDate;
    	realizedPriceUrl = createUrl(theFileName);
    }
    
	@Override
	public void execute() {
		
		PriceUpdater aPriceUpdater = null;
		
		if (isPricePageAvailable())
		{
			aPriceUpdater = new HtmlPricePageUpdater();
		} 
		else
		{
			aPriceUpdater = new PdfPricePageUpdater();
		}
		aPriceUpdater.updatePrice();
	}
	
	private boolean isPricePageAvailable()
	{
		try {
			URLConnection openConnection = new URL(realizedPriceUrl).openConnection();
			return openConnection.getContentLength() >0 ? true:false;
		} catch (Exception e) {
			e.printStackTrace();
		}
		return false;
	}
	
	private String createUrl(String theFileName) {
		 // try to find the current auction tag
       Matcher matcher = anAuctionPattern.matcher(theFileName);
       if (matcher.matches())
       {
	       	String url = WERMUTH_BASE_HTTP_URL +  matcher.group(1) + ".html";
	       	System.out.println("Found url : "  + url);
	       	return url;
       }	
       throw new IllegalStateException("Can't detect URL " + theFileName + " for price updates !");
	}
	
	interface PriceUpdater {
		void updatePrice();
	}
	
	@SuppressWarnings({ "rawtypes" })
	class HtmlPricePageUpdater implements PriceUpdater{

		@Override
		public void updatePrice()  {
			try {
				updateRealizedPrices();
			} catch (Exception e) {
				e.printStackTrace();
			}
		}
		
		private final void updateRealizedPrices() throws IOException, ResourceException, ScriptException, InstantiationException, IllegalAccessException {
			ClassLoader parent = getClass().getClassLoader();
			GroovyClassLoader loader = new GroovyClassLoader(parent);
			try {
				
				Class groovyClass = loader.parseClass(new File("src/ch/persi/java/vino/importers/wermuth/PricePageParser.groovy"));
				
				GroovyObject groovyObject = (GroovyObject) groovyClass.newInstance();
				Object returnValue = groovyObject.invokeMethod("getRealizedPrices", realizedPriceUrl);
				
				if (returnValue instanceof Map) {
					Map aMap = (Map) returnValue;
					
					for (Object o : aMap.entrySet()) {
						Map.Entry anEntry = (Map.Entry) o;
						Object key = anEntry.getKey();
						Object aValue = anEntry.getValue();
						
						if (key instanceof String && (aValue == null || aValue instanceof BigDecimal))
						{
							
							String aLotNo = (String) key;
							BigDecimal aRealizedPrice = (BigDecimal) aValue;
							
							Offering aFoundOffering = dao.findOfferingByLotNumberAndDate(aLotNo,auctionDate.toDate());
							if (aFoundOffering != null)
							{
								aFoundOffering.setRealizedPrice(aRealizedPrice);
								dao.update(aFoundOffering);
							}
						}
					}
				}		
				
			}
			finally
			{
				loader.close();
			}
		}
	}
	
	class PdfPricePageUpdater implements PriceUpdater {

		@Override
		public void updatePrice() {
			// FIXME: implementation missing, parsing yet another PDF File to get the prices....
			
		}
		
	}
}
