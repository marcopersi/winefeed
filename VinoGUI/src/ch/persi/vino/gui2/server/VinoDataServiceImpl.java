package ch.persi.vino.gui2.server;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

import ch.persi.vino.gui2.client.marketdata.service.VinoDaoService;
import ch.persi.vino.gui2.shared.WineOffering;

import com.google.gwt.user.server.rpc.RemoteServiceServlet;

public class VinoDataServiceImpl extends RemoteServiceServlet implements
		VinoDaoService {

	/**
	 * 
	 */
	private static final long serialVersionUID = -5473326202804219814L;

	@Override
	public List<WineOffering> fetch(Integer startRow, Integer endRow,
			String sortBy, Map<String, String> filterCriteria) {
		System.out.println("Server fetch: approaching filterCriteria: " + filterCriteria);
		
		WineOffering aWineOffering = new WineOffering();
		aWineOffering.setCountryCode("IT");
		aWineOffering.setId(0x123L);
		aWineOffering.setLatestPrice("520");
		aWineOffering.setLatestRating("99");
		aWineOffering.setOrigin("Bolgheri");
		aWineOffering.setRatingAgency("Parker");
		aWineOffering.setVintage("2006");
		aWineOffering.setWineName("Masseto");
		List<WineOffering> someOfferings = new ArrayList<>();
		someOfferings.add(aWineOffering);
		return someOfferings;
	}

	@Override
	public WineOffering add(WineOffering theData) {
		System.out.println("Server add called");
		return null;
	}

	@Override
	public WineOffering update(WineOffering theData) {
		System.out.println("Server update called");
		return null;
	}

	@Override
	public void remove(WineOffering theData) {
		System.out.println("Server remove called");
	}

}
