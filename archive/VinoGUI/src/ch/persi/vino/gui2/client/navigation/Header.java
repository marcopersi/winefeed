package ch.persi.vino.gui2.client.navigation;

import com.google.gwt.core.client.GWT;
import com.smartgwt.client.types.Alignment;
import com.smartgwt.client.widgets.Img;
import com.smartgwt.client.widgets.Label;
import com.smartgwt.client.widgets.layout.HLayout;

public class Header extends HLayout {

	/**
	 * the height of the top header !
	 */
	private static final int HEIGHT = 58;

	public Header()
	{
		super();

		GWT.log("initialization of the header area runs", null);
		
		init();
		
		initContent();
	}

	private final void init()
	{
		setStyleName("vino-Header");
	    setHeight(HEIGHT);
	}
	
	private final void initContent(){
		Img logo = new Img("logo.png", 48, 48);
		logo.setStyleName("vino-Header-Logo");
		
		Label name = new Label(); 
		name.setStyleName("vino-Header-Name");
		name.setContents("Vino");

		// initialise the West layout container
	    HLayout westLayout = new HLayout();
	    westLayout.setHeight(HEIGHT);	
	    westLayout.setWidth("50%");
	    westLayout.addMember(logo);
	    westLayout.addMember(name);
	    
	    // initialise the Signed In User label
		Label signedInUser = new Label();  
		signedInUser.setStyleName("vino-Header-SignedInUser");  
		signedInUser.setContents("<b>Marco Persi</b><br />wineInvestment Ltd.");   

	    // initialise the East layout container
	    HLayout eastLayout = new HLayout();
	    eastLayout.setAlign(Alignment.RIGHT);  
	    eastLayout.setHeight(HEIGHT);
	    eastLayout.setWidth("50%");
	    eastLayout.addMember(signedInUser);	
	    
	    // add the West and East layout containers to the Masthead layout container
		addMember(westLayout);  	
		addMember(eastLayout); 
		
	}
}
