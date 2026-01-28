package ch.persi.java.vino.importers.wermuth
import org.apache.commons.lang3.math.NumberUtils;
	
	
	public Map extractByPair(groovy.util.slurpersupport.NodeChildren a)
	{
		SortedMap aValuesMap = new TreeMap();
		
		for (int i=3; i<a.size();i++)
		{
				// creating a numeric value for the key, here bigdecimal
				String aKeyValue = a[i].toString().trim();
				
				// the value
				def x = a[++i].toString();
				if (NumberUtils.isNumber(x))
				{
					BigDecimal aValue = new BigDecimal(x);
					aValuesMap.put(aKeyValue, aValue);
				} else
				{
					aValuesMap.put(aKeyValue, null);
				}
		}
		return aValuesMap;
	}
	
	public Map extractByIndex(groovy.util.slurpersupport.NodeChildren a)
	{
		SortedMap aValuesMap = new TreeMap();
		
		for (int i=6; i<a.size();i++)
		{
			// creating a numeric value for the key, here big decimal
			String aKeyValue = a[i].toString().trim();
			++i;++i;
			
			// the value
			def x = a[++i].toString();
			if (NumberUtils.isNumber(x))
			{
				BigDecimal aValue = new BigDecimal(x);
				aValuesMap.put(aKeyValue, aValue);
			} else
			{
				aValuesMap.put(aKeyValue, null);
			}
		}
		return aValuesMap;
	}

public Map getRealizedPrices(String theUrl)
{
	def slurper = new XmlSlurper(new org.ccil.cowan.tagsoup.Parser())

	SortedMap aValuesMap = new TreeMap();

	def key=null;
	def value;
	
	html = slurper.parse(theUrl)
	def allPairs = html.body.table.tr.td;
	def sizeOfColumns = html.body.table.tr;
	
	if (html.body.table.tr[3].td.size()==2)
	{
		aValuesMap = extractByPair(allPairs);
	} else
	{
		aValuesMap = extractByIndex(allPairs);
	}
	
	println "Size is: " + aValuesMap.size();
	println aValuesMap;
	return aValuesMap;
}