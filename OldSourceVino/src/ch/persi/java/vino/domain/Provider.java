package ch.persi.java.vino.domain;

import org.apache.commons.lang3.builder.ReflectionToStringBuilder;

public class Provider {
	private String name;
	private long id;

	public Provider()
	{
		super();
	}
	
	public Provider(String name) {
		super();
		this.name = name;
	}


	public String getName() {
		return name;
	}

	public void setName(String name) {
		this.name = name;
	}


	public long getId() {
		return id;
	}


	public void setId(long id) {
		this.id = id;
	}
	
	@Override
	public String toString()
	{
		ReflectionToStringBuilder aBuilder = new ReflectionToStringBuilder(this);
		return aBuilder.toString();		
	}
}
