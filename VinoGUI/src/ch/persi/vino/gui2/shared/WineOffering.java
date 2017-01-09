package ch.persi.vino.gui2.shared;

import com.google.gwt.user.client.rpc.IsSerializable;
// this is the hook for the connectivity to vino server part !
public class WineOffering implements IsSerializable {

	private long id;
	private String wineName;
	private String vintage;
	private String latestRating;
	private String latestPrice;
	private String origin;
	private String countryCode;
	private String ratingAgency;
	
	public long getId() {
		return id;
	}
	public void setId(long theId) {
		this.id = theId;
	}
	public String getWineName() {
		return wineName;
	}
	public void setWineName(String theWineName) {
		this.wineName = theWineName;
	}
	public String getVintage() {
		return vintage;
	}
	public void setVintage(String theVintage) {
		this.vintage = theVintage;
	}
	public String getLatestRating() {
		return latestRating;
	}
	public void setLatestRating(String theLatestRating) {
		this.latestRating = theLatestRating;
	}
	public String getLatestPrice() {
		return latestPrice;
	}
	public void setLatestPrice(String theLatestPrice) {
		this.latestPrice = theLatestPrice;
	}
	public String getOrigin() {
		return origin;
	}
	public void setOrigin(String theOrigin) {
		this.origin = theOrigin;
	}
	public String getCountryCode() {
		return countryCode;
	}
	public void setCountryCode(String theCountryCode) {
		this.countryCode = theCountryCode;
	}
	public String getRatingAgency() {
		return ratingAgency;
	}
	public void setRatingAgency(String theRatingAgency) {
		this.ratingAgency = theRatingAgency;
	}
	
	
}
