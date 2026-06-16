package tara.bozin.smartbabyroom;

import android.os.Bundle;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.SeekBar;
import android.widget.TextView;

import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.fragment.app.Fragment;

import org.json.JSONObject;

public class LightFragment extends Fragment
{

    private TextView tvLampState;
    private TextView tvBrightness;
    private SeekBar seekBrightness;
    private int brightness = 0;
    private MQTTManager mqttManager;

    @Override
    public View onCreateView(LayoutInflater inflater, ViewGroup container, Bundle savedInstanceState)
    {
        View view = inflater.inflate(R.layout.fragment_light, container, false);
        mqttManager = MQTTManager.getInstance();

        tvLampState = view.findViewById(R.id.tvLampState);
        tvBrightness = view.findViewById(R.id.tvBrightness);

        seekBrightness = view.findViewById(R.id.seekBrightness);

        Button btnSendBrightness = view.findViewById(R.id.btnSendBrightness);

        JSONObject state = mqttManager.getLastState();
        if (state != null)
        {
            updateFromState(state);
        }

        seekBrightness.setOnSeekBarChangeListener(new SeekBar.OnSeekBarChangeListener()
        {
            @Override
            public void onProgressChanged(SeekBar seekBar, int progress, boolean fromUser)
            {
                brightness = progress;
                updateUi();
            }

            @Override
            public void onStartTrackingTouch(SeekBar seekBar) {}

            @Override
            public void onStopTrackingTouch(SeekBar seekBar) {}
        });

        mqttManager.setParentStateListener(parentState ->
        {
            requireActivity().runOnUiThread(() ->
            {
                updateFromState(parentState);
            });
        });

        btnSendBrightness.setOnClickListener(v -> sendBrightness());
        updateUi();
        return view;
    }

    private void sendBrightness()
    {
        mqttManager.publishParentCommand("SET_LAMP_BRIGHTNESS", brightness);
        updateUi();
    }

    private void updateUi()
    {
        tvBrightness.setText(getString(R.string.brightness_value, brightness));

        if (brightness == 0)
        {
            tvLampState.setText(R.string.lamp_off);
        }
        else
        {
            tvLampState.setText(R.string.lamp_on);
        }
    }

    private void updateFromState(JSONObject state)
    {
        int brightness = state.optInt("brightness", 0);
        String lamp = state.optString("lamp", "OFF");

        this.brightness = brightness;

        tvLampState.setText(getString(R.string.lamp_state, lamp));
        tvBrightness.setText(getString(R.string.brightness_value, brightness));
        seekBrightness.setProgress(brightness);
    }
}