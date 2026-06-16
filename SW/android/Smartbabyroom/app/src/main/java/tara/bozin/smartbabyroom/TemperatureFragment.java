package tara.bozin.smartbabyroom;

import android.os.Bundle;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.TextView;

import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.fragment.app.Fragment;

import org.json.JSONObject;

public class TemperatureFragment extends Fragment
{
    TextView tvCurrentTemperature;
    TextView tvHeaterState;
    TextView tvFanState;
    Button btnHeaterToggle;
    Button btnFanToggle;

    private boolean heaterOn = false;
    private boolean fanOn = false;

    private MQTTManager mqttManager;

    @Override
    public View onCreateView(LayoutInflater inflater, ViewGroup container, Bundle savedInstanceState)
    {
        View view = inflater.inflate(R.layout.fragment_temperature, container, false);
        mqttManager = MQTTManager.getInstance();

        tvCurrentTemperature = view.findViewById(R.id.tvCurrentTemperature);
        tvHeaterState = view.findViewById(R.id.tvHeaterState);
        tvFanState = view.findViewById(R.id.tvFanState);

        Button btnRefreshTemperature = view.findViewById(R.id.btnRefreshTemperature);
        btnHeaterToggle = view.findViewById(R.id.btnHeaterToggle);
        btnFanToggle = view.findViewById(R.id.btnFanToggle);

        JSONObject state = mqttManager.getLastState();
        if (state != null)
        {
            updateFromState(state);
        }

        btnRefreshTemperature.setOnClickListener(v -> refreshTemperature());
        btnHeaterToggle.setOnClickListener(v -> toggleHeater());
        btnFanToggle.setOnClickListener(v -> toggleFan());

        mqttManager.setParentStateListener(parentState ->
        {
            requireActivity().runOnUiThread(() ->
            {
                updateFromState(parentState);
            });
        });
        updateUi();
        return view;
    }

    private void refreshTemperature()
    {
        mqttManager.publishParentCommand("GET_TEMPERATURE");

        tvCurrentTemperature.setText(R.string.Temp_req);
    }

    private void toggleHeater()
    {
        heaterOn = !heaterOn;
        if (heaterOn)
        {
            fanOn = false;
            mqttManager.publishParentCommand("HEATER_ON");
        }
        else
        {
            mqttManager.publishParentCommand("HEATER_OFF");
        }
        updateUi();
    }

    private void toggleFan()
    {
        fanOn = !fanOn;
        if (fanOn)
        {
            heaterOn = false;
            mqttManager.publishParentCommand("FAN_ON");
        }
        else
        {
            mqttManager.publishParentCommand("FAN_OFF");
        }
        updateUi();
    }

    private void updateUi()
    {
        tvHeaterState.setText(heaterOn ? "Heater: ON" : "Heater: OFF");
        btnHeaterToggle.setText(heaterOn ? "Turn Heater OFF" : "Turn Heater ON");

        tvFanState.setText(fanOn ? "Fan: ON" : "Fan: OFF");
        btnFanToggle.setText(fanOn ? "Turn Fan OFF" : "Turn Fan ON");
    }

    private void updateFromState(JSONObject state)
    {
        double temp = state.optDouble("temperature", 0);
        String fan = state.optString("fan", "OFF");
        String heater = state.optString("heater", "OFF");

        tvCurrentTemperature.setText(getString(R.string.current_temperature, temp));
        tvFanState.setText(getString(R.string.fan_state, fan));
        tvHeaterState.setText(getString(R.string.heater_state, heater));

        heaterOn = heater.equals("ON");
        fanOn = fan.equals("ON");

        btnHeaterToggle.setText(heaterOn ? "Turn Heater OFF" : "Turn Heater ON");
        btnFanToggle.setText(fanOn ? "Turn Fan OFF" : "Turn Fan ON");
    }
}