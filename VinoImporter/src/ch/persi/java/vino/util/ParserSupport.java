package ch.persi.java.vino.util;

import static org.apache.commons.lang3.ArrayUtils.isEmpty;

public class ParserSupport {

	/**
	 * PDF parsing seems to be a challenge for PDF parsing libraries. 
	 * One has to expect that Strings are returned containing unreasonable spaces.
	 * If these Strings should be processed, this could lead into problems, therefore this method
	 * compacts the strings in a way, that leading & trailing space characters become removed
	 * 
	 * @param theStrings
	 * @return an array of {@link String} as a copy of the input, but the input Strings were cleaned from containing spaces
	 */
	String[] compact(String[] theStrings)
	{
		if (isEmpty(theStrings))
		{
			return new String[0];
		}
		
		String[] someCompactedStrings = new String[theStrings.length];
		for (int i=0;i<someCompactedStrings.length;i++)
		{
			someCompactedStrings[i]=compact(theStrings[i]);
		}
		return someCompactedStrings;
	}
	
	private static final String compact(String aString)
	{
		return aString.replaceAll("^ +| +$|( )+", "$1");
	}
}
