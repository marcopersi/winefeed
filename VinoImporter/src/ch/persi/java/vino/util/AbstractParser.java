package ch.persi.java.vino.util;

import java.util.List;
import static org.apache.commons.lang3.ArrayUtils.isEmpty;

public abstract class AbstractParser implements InputParser {

	@Override
	public abstract List<String> parse(String theFileName);

	/**
	 * PDF parsing seems to be quite a challenge for PDF parsers. 
	 * One has to expect that Strings are returned containing a huge amount of unreasonable spaces.
	 * If these Strings should be processed then, this could lead into problems, therefore this method
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
