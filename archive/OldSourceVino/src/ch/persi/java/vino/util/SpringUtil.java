package ch.persi.java.vino.util;

import org.springframework.context.support.ClassPathXmlApplicationContext;

public class SpringUtil {

	
	private static ClassPathXmlApplicationContext context;
	
	public static ClassPathXmlApplicationContext getContext()
	{
		if (context == null)
		{
			context = new ClassPathXmlApplicationContext("classpath:config.xml");
		}
		return context;
	}
	
}
