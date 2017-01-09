package ch.persi.java.vino.domain;

import java.util.HashSet;
import java.util.Set;

public class Wine {

	private long id;
	private int vintage;
	private String origin; 
	private String name;
	private String region;
	private String producer;
	
	@SuppressWarnings("rawtypes")
	private Set ratings= null;
	
	
	/**
	 * 
	 * @param theVintage vintage of the wine
	 * @param theOrigin	origin of the wine, MO/DOC,MO,DOC,IGT usw.
	 * @param theName the wines name
	 * @param region the region of the wine, e.g. Bolgheri oder Toscana oder Pomerol/Bordeaux
	 * @param producer the producer e.g. Tenuta San Guido...
	 * 
	 */
	public Wine(int theVintage, String theOrigin, String theName, String region, String producer ) {
		super();
		this.vintage=theVintage;
		this.origin=theOrigin;
		name = theName;
		this.region = region;
		this.producer = producer;
	}
	
	public Wine() {
		super();
	}

	public String getProducer() {
		return producer;
	}

	public void setProducer(String producer) {
		this.producer = producer;
	}

	public String getRegion() {
		return region;
	}

	public void setRegion(String region) {
		this.region = region;
	}

	@SuppressWarnings("rawtypes")
	public Set getRatings() {
		return ratings;
	}

	@SuppressWarnings("rawtypes")
	public void setRatings(Set theRatings) {
		ratings = theRatings;
	}
	
	@SuppressWarnings({ "rawtypes", "unchecked" })
	public void addRating(Rating theRating)
	{
		if (this.ratings == null)
		{
			ratings = new HashSet();
		}
		ratings.add(theRating);
	}
	
	public long getId() {
		return id;
	}
	
	public void setId(long id) {
		this.id = id;
	}

	public int getVintage() {
		return vintage;
	}

	public void setVintage(int year) {
		this.vintage = year;
	}
	public String getOrigin() {
		return origin;
	}

	public void setOrigin(String origin) {
		this.origin = origin;
	}

	public void setName(String name) {
		this.name = name;
	}

	public String getName() {
		return name;
	}

	@Override
	public String toString()
	{
		StringBuilder aBuilder = new StringBuilder();
		aBuilder.append("name=");
		aBuilder.append(this.name);
		aBuilder.append(",");
		aBuilder.append("origin=");
		aBuilder.append(this.origin);
		aBuilder.append(",");
		aBuilder.append("producer=");
		aBuilder.append(this.producer);
		aBuilder.append(",");
		aBuilder.append("region=");
		aBuilder.append(this.region);
		aBuilder.append(",");
		aBuilder.append("vintage=");
		aBuilder.append(this.vintage);

		if (ratings != null && ratings.size()>0){
			aBuilder.append(",");

			for(int i=0;i<=ratings.size();i++)
			{
				aBuilder.append(ratings.toString());
				if (i<ratings.size())
				{
					aBuilder.append(",");
				}
			}
		}
		return aBuilder.toString();
	}
	
}
